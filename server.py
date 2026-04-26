import asyncio, json, os, sys, threading, time, subprocess, mimetypes, uuid
from pathlib import Path
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PORT = 8080
WS_PORT = 8081
URL = f"http://127.0.0.1:{PORT}"

# Support both normal Python and PyInstaller frozen exe
if getattr(sys, 'frozen', False):
    _BASE = Path(sys._MEIPASS)
else:
    _BASE = Path(__file__).resolve().parent
WEB_DIST = _BASE / "web-ui" / "dist"

mcp = FastMCP("mymcp", host="127.0.0.1", port=PORT, streamable_http_path="/mcp", stateless_http=True)

# ---------------------------------------------------------------------------
# Multi-session state (single process — all IDEs connect here)
# ---------------------------------------------------------------------------
_sessions: dict[str, dict] = {}   # sid -> session dict
_lock = threading.Lock()
_version = 0                      # global change counter
_change_evt = threading.Event()   # signalled on any state change
_ws_started = False
_last_access = 0.0


def _new_session(ai_msg: str = "", source: str = "", project: str = "", model: str = "") -> dict:
    history = []
    if ai_msg:
        history.append({"role": "ai", "content": ai_msg, "ts": time.time(), "model": model})
    return {
        "sid": uuid.uuid4().hex[:8],
        "ai_msg": ai_msg,
        "user_msg": "",
        "user_images": [],
        "phase": "idle",
        "msg_id": 0,
        "evt": threading.Event(),
        "created": time.time(),
        "updated": time.time(),
        "source": source,
        "project": project,
        "model": model,
        "history": history,
        "_listener": False,
        # API bridge fields
        "_api_waiting": False,
        "_api_response_evt": threading.Event(),
        "_api_response": "",
    }


def _signal_change():
    global _version
    _version += 1
    _change_evt.set()
    _change_evt.clear()
    _broadcast_sessions()


def _session_state(s: dict) -> dict:
    return {
        "sid": s["sid"],
        "ai_msg": s["ai_msg"],
        "phase": s["phase"],
        "msg_id": s["msg_id"],
        "ts": s["updated"],
    }


def _sessions_list() -> dict:
    with _lock:
        items = []
        active_sid = ""
        for s in _sessions.values():
            items.append({
                "sid": s["sid"],
                "phase": s["phase"],
                "msg_id": s["msg_id"],
                "preview": (s["history"][0]["content"][:80] if s.get("history") else (s["ai_msg"] or "")[:80]),
                "msg_count": len(s.get("history", [])),
                "created": s["created"],
                "updated": s["updated"],
                "source": s["source"],
                "project": s["project"],
                "model": s.get("model", ""),
                "alive": bool(s.get("_listener")) or s["phase"] == "waiting_for_ai",
            })
            if s["phase"] == "waiting_for_user" and not active_sid:
                active_sid = s["sid"]
        if not active_sid and items:
            active_sid = max(items, key=lambda x: x["updated"])["sid"]
        return {"sessions": items, "active_sid": active_sid}


# ---------------------------------------------------------------------------
# WebSocket server for Web UI real-time updates (port 8081)
# ---------------------------------------------------------------------------
_ws_clients: set = set()
_ws_loop: asyncio.AbstractEventLoop | None = None

try:
    import websockets
    import websockets.asyncio.server as ws_server
    _HAS_WS = True
except ImportError:
    _HAS_WS = False


async def _ws_handler(websocket):
    global _last_access
    websocket._mcp_sid = ""
    _ws_clients.add(websocket)
    _last_access = time.monotonic()
    try:
        async for raw in websocket:
            _last_access = time.monotonic()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            msg_type = data.get("type", "")

            if msg_type == "ping":
                await websocket.send(json.dumps({"type": "pong"}))

            elif msg_type == "join":
                client_sid = data.get("sid", "")
                websocket._mcp_sid = client_sid
                with _lock:
                    s = _sessions.get(client_sid)
                if s:
                    await websocket.send(json.dumps(_session_state(s), ensure_ascii=False))
                else:
                    await websocket.send(json.dumps({"error": "no_session"}))
                await websocket.send(json.dumps({"type": "sessions", **_sessions_list()}, ensure_ascii=False))

            elif msg_type == "list_sessions":
                await websocket.send(json.dumps({"type": "sessions", **_sessions_list()}, ensure_ascii=False))

            elif msg_type == "submit":
                sid = data.get("sid", "")
                response = data.get("response", "")
                images = data.get("images", [])
                with _lock:
                    s = _sessions.get(sid)
                if s and response:
                    msg = response
                    s["user_msg"] = msg
                    s["user_images"] = images
                    entry: dict = {"role": "user", "content": msg, "ts": time.time()}
                    if images:
                        entry["images"] = images
                    s["history"].append(entry)
                    s["phase"] = "waiting_for_ai"
                    s["updated"] = time.time()
                    s["evt"].set()
                    _signal_change()
                    _broadcast_state(sid)
                    await websocket.send(json.dumps({"type": "ack"}))
                else:
                    await websocket.send(json.dumps({"error": "invalid_submit"}))

    except Exception:
        pass
    finally:
        _ws_clients.discard(websocket)


def _broadcast_sessions():
    """Push sessions list to all connected WS clients."""
    if not _HAS_WS or not _ws_loop:
        return
    payload = json.dumps({"type": "sessions", **_sessions_list()}, ensure_ascii=False)

    async def _push():
        dead = []
        for ws in list(_ws_clients):
            try:
                await ws.send(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            _ws_clients.discard(ws)

    try:
        asyncio.run_coroutine_threadsafe(_push(), _ws_loop)
    except Exception:
        pass


def _broadcast_state(sid: str):
    """Push state update for a specific session to subscribed WS clients."""
    if not _HAS_WS or not _ws_loop:
        return
    with _lock:
        s = _sessions.get(sid)
    if not s:
        return
    payload = json.dumps(_session_state(s), ensure_ascii=False)

    async def _push():
        dead = []
        for ws in list(_ws_clients):
            ws_sid = getattr(ws, '_mcp_sid', '')
            if ws_sid == sid:
                try:
                    await ws.send(payload)
                except Exception:
                    dead.append(ws)
        for ws in dead:
            _ws_clients.discard(ws)

    try:
        asyncio.run_coroutine_threadsafe(_push(), _ws_loop)
    except Exception:
        pass


async def _ws_main():
    global _ws_loop
    _ws_loop = asyncio.get_running_loop()
    async with ws_server.serve(_ws_handler, "127.0.0.1", WS_PORT, max_size=50 * 1024 * 1024):
        await asyncio.Future()


def _start_ws():
    if not _HAS_WS:
        print("[MCP Chat] websockets not installed, WS disabled", file=sys.stderr)
        return
    try:
        asyncio.run(_ws_main())
    except Exception as e:
        print(f"[MCP Chat] WS error: {e}", file=sys.stderr)


def _ensure_ws():
    global _ws_started
    with _lock:
        if not _ws_started:
            _ws_started = True
            threading.Thread(target=_start_ws, daemon=True).start()


# ---------------------------------------------------------------------------
# HTTP API routes — served via FastMCP custom_route (Starlette)
# ---------------------------------------------------------------------------
def _guess_mime(path: str) -> str:
    mt, _ = mimetypes.guess_type(path)
    return mt or "application/octet-stream"


@mcp.custom_route("/", methods=["GET"])
async def serve_index(request):
    from starlette.responses import HTMLResponse, Response
    index = WEB_DIST / "index.html"
    if index.exists():
        return HTMLResponse(index.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>MCP Chat</h1><p>Frontend not built. Run <code>npm run build</code> in web-ui/</p>")


@mcp.custom_route("/chat", methods=["GET"])
async def serve_chat(request):
    return await serve_index(request)


@mcp.custom_route("/index.html", methods=["GET"])
async def serve_index_html(request):
    return await serve_index(request)


@mcp.custom_route("/assets/{path:path}", methods=["GET"])
async def serve_assets(request):
    from starlette.responses import Response
    rel = request.path_params.get("path", "")
    fp = WEB_DIST / "assets" / rel
    if fp.exists() and fp.is_file():
        return Response(fp.read_bytes(), media_type=_guess_mime(str(fp)))
    return Response(status_code=404)


@mcp.custom_route("/favicon.ico", methods=["GET"])
async def serve_favicon(request):
    from starlette.responses import Response
    fp = WEB_DIST / "favicon.ico"
    if fp.exists():
        return Response(fp.read_bytes(), media_type="image/x-icon")
    return Response(status_code=404)


@mcp.custom_route("/avatar.png", methods=["GET"])
async def serve_avatar(request):
    from starlette.responses import Response
    fp = WEB_DIST / "avatar.png"
    if fp.exists():
        return Response(fp.read_bytes(), media_type="image/png")
    return Response(status_code=404)


@mcp.custom_route("/user.jpg", methods=["GET"])
async def serve_user_avatar(request):
    from starlette.responses import Response
    fp = WEB_DIST / "user.jpg"
    if fp.exists():
        return Response(fp.read_bytes(), media_type="image/jpeg")
    return Response(status_code=404)


@mcp.custom_route("/poll", methods=["GET"])
async def api_poll(request):
    global _last_access
    _last_access = time.monotonic()
    from starlette.responses import JSONResponse, Response
    params = dict(request.query_params)
    sid = params.get("sid", "")
    v = int(params.get("v", "0"))
    if v and v >= _version:
        await asyncio.get_running_loop().run_in_executor(None, _change_evt.wait, 30)
        if _version == v:
            return Response(status_code=304)
    result: dict = {"v": _version}
    with _lock:
        s = _sessions.get(sid)
    if s:
        result["state"] = _session_state(s)
    result.update(_sessions_list())
    return JSONResponse(result)


@mcp.custom_route("/status", methods=["GET"])
async def api_status(request):
    from starlette.responses import JSONResponse
    params = dict(request.query_params)
    sid = params.get("sid", "")
    with _lock:
        s = _sessions.get(sid)
    if s:
        return JSONResponse(_session_state(s))
    return JSONResponse({"ai_msg": "", "phase": "idle", "msg_id": 0})


@mcp.custom_route("/submit", methods=["POST"])
async def api_submit(request):
    global _last_access
    _last_access = time.monotonic()
    from starlette.responses import JSONResponse
    data = await request.json()
    sid = data.get("sid", "")
    response = data.get("response", "")
    images = data.get("images", [])
    with _lock:
        s = _sessions.get(sid)
    if not s:
        return JSONResponse({"ok": False, "error": "no_session"})
    if not response:
        return JSONResponse({"ok": False, "error": "empty_response"})
    msg = response
    s["user_msg"] = msg
    s["user_images"] = images
    entry: dict = {"role": "user", "content": msg, "ts": time.time()}
    if images:
        entry["images"] = images
    s["history"].append(entry)
    s["phase"] = "waiting_for_ai"
    s["updated"] = time.time()
    s["evt"].set()
    _signal_change()
    _broadcast_state(sid)
    return JSONResponse({"ok": True, **_session_state(s)})


@mcp.custom_route("/history", methods=["GET"])
async def api_history(request):
    from starlette.responses import JSONResponse
    params = dict(request.query_params)
    sid = params.get("sid", "")
    with _lock:
        s = _sessions.get(sid)
    if not s:
        return JSONResponse({"history": []})
    return JSONResponse({"history": s.get("history", [])}, headers={"Cache-Control": "no-cache"})


@mcp.custom_route("/delete", methods=["POST"])
async def api_delete(request):
    from starlette.responses import JSONResponse
    data = await request.json()
    sid = data.get("sid", "")
    with _lock:
        removed = _sessions.pop(sid, None)
    if removed:
        _signal_change()
    return JSONResponse({"ok": True})


@mcp.custom_route("/delete-project", methods=["POST"])
async def api_delete_project(request):
    from starlette.responses import JSONResponse
    data = await request.json()
    project = data.get("project", "")
    with _lock:
        to_remove = [sid for sid, s in _sessions.items()
                     if (s["project"] or "(default)") == project]
        for sid in to_remove:
            _sessions.pop(sid, None)
    if to_remove:
        _signal_change()
    return JSONResponse({"ok": True})


# ---------------------------------------------------------------------------
# Vault / File-system API (Obsidian-style notes)
# ---------------------------------------------------------------------------
VAULT_ROOT: Path | None = None          # Set via /vault/config
VAULT_EXTS = {".md", ".txt", ".json", ".yaml", ".yml", ".csv", ".log"}


def _vault_root() -> Path | None:
    global VAULT_ROOT
    if VAULT_ROOT and VAULT_ROOT.is_dir():
        return VAULT_ROOT
    return None


def _safe_path(root: Path, rel: str) -> Path | None:
    """Resolve *rel* under *root* and ensure it doesn't escape."""
    try:
        p = (root / rel).resolve()
        if str(p).startswith(str(root.resolve())):
            return p
    except Exception:
        pass
    return None


@mcp.custom_route("/vault/config", methods=["GET", "POST"])
async def vault_config(request):
    global VAULT_ROOT
    from starlette.responses import JSONResponse
    if request.method == "POST":
        body = await request.json()
        vp = body.get("path", "")
        p = Path(vp).resolve()
        if p.is_dir():
            VAULT_ROOT = p
            return JSONResponse({"ok": True, "path": str(VAULT_ROOT)})
        return JSONResponse({"ok": False, "error": "目录不存在"}, status_code=400)
    return JSONResponse({"path": str(VAULT_ROOT) if VAULT_ROOT else None})


@mcp.custom_route("/vault/tree", methods=["GET"])
async def vault_tree(request):
    from starlette.responses import JSONResponse
    root = _vault_root()
    if not root:
        return JSONResponse({"error": "vault not configured"}, status_code=400)
    rel = request.query_params.get("path", "")
    base = _safe_path(root, rel)
    if not base or not base.is_dir():
        return JSONResponse({"error": "invalid path"}, status_code=400)

    items = []
    try:
        for entry in sorted(base.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            if entry.name.startswith("."):
                continue
            if entry.is_dir():
                child_count = sum(1 for c in entry.iterdir() if not c.name.startswith("."))
                items.append({"name": entry.name, "type": "dir", "children": child_count})
            elif entry.suffix.lower() in VAULT_EXTS:
                items.append({"name": entry.name, "type": "file", "size": entry.stat().st_size,
                              "mtime": entry.stat().st_mtime})
    except PermissionError:
        pass
    return JSONResponse(items)


@mcp.custom_route("/vault/read", methods=["GET"])
async def vault_read(request):
    from starlette.responses import JSONResponse, PlainTextResponse
    root = _vault_root()
    if not root:
        return JSONResponse({"error": "vault not configured"}, status_code=400)
    rel = request.query_params.get("path", "")
    fp = _safe_path(root, rel)
    if not fp or not fp.is_file():
        return JSONResponse({"error": "file not found"}, status_code=404)
    try:
        return PlainTextResponse(fp.read_text(encoding="utf-8"))
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@mcp.custom_route("/vault/write", methods=["POST"])
async def vault_write(request):
    from starlette.responses import JSONResponse
    root = _vault_root()
    if not root:
        return JSONResponse({"error": "vault not configured"}, status_code=400)
    body = await request.json()
    rel = body.get("path", "")
    content = body.get("content", "")
    fp = _safe_path(root, rel)
    if not fp:
        return JSONResponse({"error": "invalid path"}, status_code=400)
    try:
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content, encoding="utf-8")
        return JSONResponse({"ok": True, "size": len(content.encode("utf-8"))})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@mcp.custom_route("/vault/mkdir", methods=["POST"])
async def vault_mkdir(request):
    from starlette.responses import JSONResponse
    root = _vault_root()
    if not root:
        return JSONResponse({"error": "vault not configured"}, status_code=400)
    body = await request.json()
    rel = body.get("path", "")
    fp = _safe_path(root, rel)
    if not fp:
        return JSONResponse({"error": "invalid path"}, status_code=400)
    try:
        fp.mkdir(parents=True, exist_ok=True)
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@mcp.custom_route("/vault/delete", methods=["POST"])
async def vault_delete(request):
    from starlette.responses import JSONResponse
    root = _vault_root()
    if not root:
        return JSONResponse({"error": "vault not configured"}, status_code=400)
    body = await request.json()
    rel = body.get("path", "")
    fp = _safe_path(root, rel)
    if not fp or fp == root:
        return JSONResponse({"error": "invalid path"}, status_code=400)
    try:
        if fp.is_file():
            fp.unlink()
        elif fp.is_dir():
            import shutil
            shutil.rmtree(fp)
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@mcp.custom_route("/vault/rename", methods=["POST"])
async def vault_rename(request):
    from starlette.responses import JSONResponse
    root = _vault_root()
    if not root:
        return JSONResponse({"error": "vault not configured"}, status_code=400)
    body = await request.json()
    old = _safe_path(root, body.get("from", ""))
    new = _safe_path(root, body.get("to", ""))
    if not old or not new or not old.exists():
        return JSONResponse({"error": "invalid path"}, status_code=400)
    try:
        new.parent.mkdir(parents=True, exist_ok=True)
        old.rename(new)
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@mcp.custom_route("/vault/search", methods=["GET"])
async def vault_search(request):
    from starlette.responses import JSONResponse
    root = _vault_root()
    if not root:
        return JSONResponse({"error": "vault not configured"}, status_code=400)
    q = request.query_params.get("q", "").lower().strip()
    if not q:
        return JSONResponse([])
    results = []
    for fp in root.rglob("*"):
        if fp.name.startswith(".") or fp.is_dir():
            continue
        if fp.suffix.lower() not in VAULT_EXTS:
            continue
        rel = str(fp.relative_to(root)).replace("\\", "/")
        if q in fp.name.lower():
            results.append({"path": rel, "match": "name"})
            continue
        try:
            text = fp.read_text(encoding="utf-8", errors="ignore")
            if q in text.lower():
                # Find context snippet
                idx = text.lower().index(q)
                start = max(0, idx - 40)
                end = min(len(text), idx + len(q) + 40)
                snippet = text[start:end].replace("\n", " ")
                results.append({"path": rel, "match": "content", "snippet": snippet})
        except Exception:
            pass
        if len(results) >= 50:
            break
    return JSONResponse(results)


# ---------------------------------------------------------------------------
# Stale session auto-cleanup (listener-based)
# ---------------------------------------------------------------------------
CLEANUP_INTERVAL = 600    # check every 10 minutes
STALE_THRESHOLD = 3600    # only remove sessions idle for > 1 hour


def _cleanup_stale() -> list[str]:
    """Remove sessions that have no active listener AND have been idle for a long time."""
    now = time.time()
    removed = []
    with _lock:
        for sid in list(_sessions):
            s = _sessions[sid]
            if not s.get("_listener") and s["phase"] == "idle" and (now - s["updated"] > STALE_THRESHOLD):
                _sessions.pop(sid)
                removed.append(sid)
    if removed:
        _signal_change()
    return removed


def _cleanup_loop():
    while True:
        time.sleep(CLEANUP_INTERVAL)
        try:
            removed = _cleanup_stale()
            if removed:
                print(f"[MCP Chat] Auto-cleanup: removed {len(removed)} stale session(s)", file=sys.stderr)
        except Exception as e:
            print(f"[MCP Chat] Cleanup error: {e}", file=sys.stderr)


threading.Thread(target=_cleanup_loop, daemon=True).start()


@mcp.custom_route("/cleanup", methods=["POST"])
async def api_cleanup(request):
    from starlette.responses import JSONResponse
    removed = _cleanup_stale()
    return JSONResponse({"ok": True, "removed": len(removed), "sids": removed})


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------
@mcp.tool()
def get_prompt() -> str:
    return (
        "# Chat Workflow\n\n"
        "chat(ai_message) is your ONLY channel to interact with the user.\n"
        "Flow: Call chat(ai_message) → Read feedback → Execute task → Call chat(ai_message) again → Loop.\n\n"
        "🚨 CRITICAL RULES:\n"
        "1. NO PLAIN REPLIES: The user CANNOT see your standard text generation. You MUST use the `ai_message` parameter to convey any information.\n"
        "2. MANDATORY CALL: After finishing ANY user task, you MUST immediately call chat(ai_message) to report back. Do not stop without calling it.\n"
        "3. Sub-agents must NEVER call chat(ai_message).\n"
        "4. Always use timeout=172800.\n"
        "5. ALWAYS pass source (your IDE name, e.g. 'Windsurf', 'Cursor', 'Copilot'), project (current workspace name), and model (the AI model you are using, e.g. 'claude-3.5-sonnet', 'gpt-4o') when calling chat()."
    )


@mcp.tool()
async def chat(ai_message: str, model: str = "", source: str = "", project: str = "") -> str:
    """Chat with the user via Web UI.

    Args:
        ai_message: The message to display to the user.
        model: Your model name (REQUIRED). e.g. "claude-sonnet-4-20250514", "gpt-4o", "gemini-2.5-pro". Always identify yourself.
        source: IDE identifier, e.g. "Windsurf", "Cursor", "Copilot".
        project: Project name or path for grouping sessions.
    """
    # Log parameters for debugging
    import logging
    logging.info(f"chat() called: model={model!r}, source={source!r}, project={project!r}")

    # Try to reuse an existing idle session from the same source+project
    session = None
    with _lock:
        for s in _sessions.values():
            if s["phase"] == "idle" and s["source"] == source and s["project"] == project:
                session = s
                break

    if session:
        # Check if there's an API client waiting for this response
        if session.get("_api_waiting") and ai_message:
            session["_api_response"] = ai_message
            session["_api_response_evt"].set()
            # Still record in history but don't show in Web UI as waiting
            session["history"].append({"role": "ai", "content": ai_message, "ts": time.time(), "model": model})

        # Reuse: append AI message to existing session
        sid = session["sid"]
        session["ai_msg"] = ai_message
        session["user_msg"] = ""
        if not session.get("_api_waiting"):
            session["history"].append({"role": "ai", "content": ai_message, "ts": time.time(), "model": model})
        session["evt"] = threading.Event()  # fresh event for this round
        session["phase"] = "waiting_for_user"
        session["msg_id"] += 1
        session["updated"] = time.time()
        if model:
            session["model"] = model
        _signal_change()
        _broadcast_state(sid)
    else:
        # Create new session
        session = _new_session(ai_message, source=source, project=project, model=model)
        sid = session["sid"]
        session["phase"] = "waiting_for_user"
        session["msg_id"] = 1
        session["updated"] = time.time()
        with _lock:
            _sessions[sid] = session
        _signal_change()
        _broadcast_state(sid)

    _ensure_ws()

    # Open browser only if no one is watching (no WS clients and no recent HTTP access)
    if not _ws_clients and time.monotonic() - _last_access > 10:
        try:
            subprocess.Popen(
                ["cmd", "/c", "start", URL],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            import webbrowser
            webbrowser.open(URL)

    # Wait for user response
    session["_listener"] = True
    try:
        await asyncio.get_running_loop().run_in_executor(None, session["evt"].wait, 259200)
    finally:
        session["_listener"] = False

    user_msg = session["user_msg"]
    user_images = session.get("user_images", [])

    # Mark session as idle (ready for next round)
    session["phase"] = "idle"
    session["updated"] = time.time()
    session["user_images"] = []  # clear after pickup
    _signal_change()
    _broadcast_state(sid)

    image_note = ""
    if user_images:
        import base64, tempfile
        saved_paths = []
        for i, img_data in enumerate(user_images):
            if isinstance(img_data, str) and img_data.startswith("data:"):
                try:
                    header, b64 = img_data.split(",", 1)
                    mime = header.split(":")[1].split(";")[0]
                    ext = mime.split("/")[-1].replace("jpeg", "jpg")
                    tmp = tempfile.NamedTemporaryFile(suffix=f".{ext}", prefix="mcp_img_", delete=False)
                    tmp.write(base64.b64decode(b64))
                    tmp.close()
                    saved_paths.append(tmp.name)
                    print(f"[MCP Chat] Saved temp image: {tmp.name}", file=sys.stderr)
                except Exception as e:
                    print(f"[MCP Chat] Image save error: {e}", file=sys.stderr)
        if saved_paths:
            paths_str = "\n".join(saved_paths)
            image_note = (
                f"\n[用户附带了 {len(saved_paths)} 张图片，已保存到以下路径，请用 read_file 工具查看:]\n"
                f"{paths_str}\n"
            )
            # Schedule cleanup after 5 minutes
            def _cleanup(paths):
                time.sleep(300)
                for p in paths:
                    try: os.unlink(p)
                    except Exception: pass
            threading.Thread(target=_cleanup, args=(saved_paths[:],), daemon=True).start()
        print(f"[MCP Chat] User attached {len(user_images)} image(s)", file=sys.stderr)

    text_reply = (
        "Here are the user responses:\n"
        "----------------------------\n"
        f"{user_msg}\n{image_note}\n\n"
        "----------------------------\n"
        "🚨 CRITICAL EXECUTION RULES:\n"
        "1. MANDATORY CALL: You MUST call chat(ai_message) immediately after completing the user's task. The user CANNOT see plain text replies.\n"
        "2. ON CANCELLATION: If any tool call is skipped or cancelled by the user, immediately call chat(ai_message) with your current progress summary.\n"
        "3. NO SUB-AGENTS: Sub-agents are STRICTLY FORBIDDEN from calling this tool.\n"
        "4. SYSTEM LIMIT: timeout=172800.\n"
        "⚠️ LAST CHANCE: This is your ONLY chance to respond before the session is interrupted!"
    )

    # Always return plain string (Windsurf MCP client doesn't support ContentBlock lists)
    return text_reply


# ---------------------------------------------------------------------------
# OpenAI-Compatible API Bridge
# ---------------------------------------------------------------------------
API_KEY = os.environ.get("MCP_API_KEY", "")  # Optional: set to require auth


def _check_api_key(request) -> str | None:
    """Return error string if API key check fails, None if ok."""
    if not API_KEY:
        return None
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
    else:
        token = request.headers.get("x-api-key", "")
    if token != API_KEY:
        return "Invalid API key"
    return None


@mcp.custom_route("/v1/chat/completions", methods=["POST"])
async def api_chat_completions(request):
    """OpenAI-compatible Chat Completions endpoint.
    Bridges external requests to the Windsurf IDE via MCP chat() flow.
    Requires an active IDE session with a listening AI.
    """
    from starlette.responses import JSONResponse, StreamingResponse
    import time as _time

    # Auth check
    err = _check_api_key(request)
    if err:
        return JSONResponse({"error": {"message": err, "type": "authentication_error"}}, status_code=401)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": {"message": "Invalid JSON", "type": "invalid_request_error"}}, status_code=400)

    messages = body.get("messages", [])
    model = body.get("model", "cascade")
    stream = body.get("stream", False)
    max_tokens = body.get("max_tokens", 4096)

    if not messages:
        return JSONResponse({"error": {"message": "messages is required", "type": "invalid_request_error"}}, status_code=400)

    # Extract the last user message
    last_user_msg = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            content = m.get("content", "")
            if isinstance(content, list):
                last_user_msg = " ".join(c.get("text", "") for c in content if c.get("type") == "text")
            else:
                last_user_msg = str(content)
            break

    if not last_user_msg:
        return JSONResponse({"error": {"message": "No user message found", "type": "invalid_request_error"}}, status_code=400)

    # Find an active session that's waiting for user input
    target_session = None
    with _lock:
        for s in _sessions.values():
            if s["phase"] == "waiting_for_user" and s.get("_listener"):
                target_session = s
                break

    if not target_session:
        return JSONResponse({
            "error": {
                "message": "No active IDE session. Make sure Windsurf IDE is running and the AI is calling chat() (e.g. tell the AI: '调用mcp-chat')",
                "type": "server_error"
            }
        }, status_code=503)

    sid = target_session["sid"]

    # Prepare API response capture
    target_session["_api_waiting"] = True
    target_session["_api_response"] = ""
    target_session["_api_response_evt"] = threading.Event()

    # Submit the user message (same as Web UI submit)
    target_session["user_msg"] = last_user_msg
    target_session["user_images"] = []
    target_session["history"].append({"role": "user", "content": last_user_msg, "ts": time.time()})
    target_session["phase"] = "waiting_for_ai"
    target_session["updated"] = time.time()
    target_session["evt"].set()
    _signal_change()
    _broadcast_state(sid)

    # Wait for the AI to call chat() again with its response
    timeout = 300  # 5 minutes max
    responded = await asyncio.get_running_loop().run_in_executor(
        None, target_session["_api_response_evt"].wait, timeout
    )

    ai_response = target_session.get("_api_response", "")
    target_session["_api_waiting"] = False

    if not responded or not ai_response:
        return JSONResponse({
            "error": {
                "message": "Timeout waiting for AI response. The IDE AI may not be responding.",
                "type": "server_error"
            }
        }, status_code=504)

    # Build OpenAI-compatible response
    completion_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    created = int(_time.time())

    if stream:
        # SSE streaming response
        async def event_stream():
            # Single chunk with full response (we get it all at once from IDE)
            chunk = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [{
                    "index": 0,
                    "delta": {"role": "assistant", "content": ai_response},
                    "finish_reason": None
                }]
            }
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            # Final chunk
            done_chunk = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
            }
            yield f"data: {json.dumps(done_chunk)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    # Non-streaming response
    return JSONResponse({
        "id": completion_id,
        "object": "chat.completion",
        "created": created,
        "model": model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": ai_response},
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": len(last_user_msg) // 4,
            "completion_tokens": len(ai_response) // 4,
            "total_tokens": (len(last_user_msg) + len(ai_response)) // 4
        }
    })


@mcp.custom_route("/v1/models", methods=["GET"])
async def api_models(request):
    """OpenAI-compatible models listing."""
    from starlette.responses import JSONResponse
    return JSONResponse({
        "object": "list",
        "data": [
            {"id": "cascade", "object": "model", "created": 1700000000, "owned_by": "windsurf"},
            {"id": "claude-sonnet-4-20250514", "object": "model", "created": 1700000000, "owned_by": "windsurf"},
            {"id": "gpt-4o", "object": "model", "created": 1700000000, "owned_by": "windsurf"},
        ]
    })


if __name__ == "__main__":
    _ensure_ws()
    print(f"[MCP Chat] API endpoint: {URL}/v1/chat/completions", file=sys.stderr)
    print(f"[MCP Chat] Models endpoint: {URL}/v1/models", file=sys.stderr)
    mcp.run(transport="streamable-http")
