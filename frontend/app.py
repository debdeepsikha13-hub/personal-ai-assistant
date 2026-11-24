"""
WOLF DevSecOps Web Server.
==========================
Built with Starlette & Uvicorn.
Provides clean REST endpoints for on-demand repository bug remediation,
OWASP/CWE cybersecurity scanning, and conversational AI engineering.

Endpoints:
  GET  /                   -> Serves the DevSecOps Studio UI
  GET  /api/status         -> Backend configuration and MCP server status
  GET  /api/tools          -> Active native and MCP engineering tools
  GET  /api/memory         -> Persistent developer context facts
  POST /api/execute_repo   -> On-demand Stage 1 (Bug Fix) -> Stage 2 (Security Scan)
  POST /api/security_audit -> On-demand OWASP/CWE SAST scan on path or inline snippet
  POST /api/chat           -> Conversational LangGraph engineering assistant
"""

import sys
import os
import asyncio
from pathlib import Path

from starlette.applications import Starlette
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route
import uvicorn

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import get_settings
from memory.user_profile_store import get_user_store
from mcp_service.config import load_mcp_server_configs

_assistant = None


def get_assistant_instance():
    """Lazy initializer for the LangGraph engineering agent."""
    global _assistant
    if _assistant is None:
        try:
            from core.agent import PersonalAssistant
            _assistant = PersonalAssistant()
        except Exception:
            _assistant = None
    return _assistant


async def homepage(request):
    """Serve the single-page DevSecOps Studio HTML."""
    html_file = Path(__file__).parent / "index.html"
    if not html_file.exists():
        return HTMLResponse("<h1>Frontend index.html not found!</h1>", status_code=404)
    return HTMLResponse(html_file.read_text(encoding="utf-8"))


async def api_status(request):
    """Return backend status, active LLM model, and MCP server count."""
    cfg = get_settings()
    mcp_configs = load_mcp_server_configs()
    store = get_user_store()

    has_api_key = bool(
        cfg.GOOGLE_API_KEY
        or cfg.OPENAI_API_KEY
        or cfg.ANTHROPIC_API_KEY
        or os.getenv("GOOGLE_API_KEY")
        or os.getenv("OPENAI_API_KEY")
    )

    return JSONResponse({
        "agent_name": cfg.AGENT_NAME,
        "provider": cfg.MODEL_PROVIDER,
        "model": cfg.MODEL_NAME,
        "has_api_key": has_api_key,
        "mcp_servers": len(mcp_configs),
        "facts_count": len(store.get_all_facts())
    })


async def api_memory(request):
    """Return stored developer context facts."""
    return JSONResponse(get_user_store().get_all_facts())


async def api_tools(request):
    """Return all active native and MCP engineering tools."""
    from tools.registry import _NATIVE_TOOLS
    from mcp_service.manager import MCPManager

    tools_data = []
    for t in _NATIVE_TOOLS:
        desc = getattr(t, "description", "")
        tools_data.append({
            "name": getattr(t, "name", str(t)),
            "description": desc.strip().split("\n")[0] if desc else "Engineering tool",
            "type": "native"
        })

    try:
        mcp_mgr = MCPManager()
        mcp_tools = await mcp_mgr.initialize()
        for t in mcp_tools:
            desc = getattr(t, "description", "")
            tools_data.append({
                "name": getattr(t, "name", str(t)),
                "description": desc.strip().split("\n")[0] if desc else "MCP tool",
                "type": "mcp"
            })
    except Exception as e:
        print(f"Note: MCP tools loading in API: {e}")

    return JSONResponse(tools_data)


async def api_decode_repo(request):
    """
    On-demand Phase 1: Target Inspection & Bug Decoding.
    Runs strictly in read-only decode mode: identifies syntax, runtime, and logic bugs
    plus OWASP/CWE cybersecurity vulnerabilities without modifying any files.
    """
    from core.repo_executor import OnDemandRepoExecutor
    try:
        body = await request.json()
        target = str(body.get("target", "")).strip()
    except Exception:
        return JSONResponse({"status": "error", "error": "Invalid JSON payload."}, status_code=400)

    if not target:
        return JSONResponse(
            {"status": "error", "error": "Please provide a GitHub repository URL or local folder path."},
            status_code=400
        )

    executor = OnDemandRepoExecutor()
    result = await asyncio.to_thread(executor.decode, target)
    return JSONResponse(result, status_code=200 if result.get("status") == "completed" else 400)


async def api_execute_repo(request):
    """
    On-demand 2-stage repository executor (Phase 2):
    Runs ONLY when the user submits a GitHub repo URL or local folder/file path.
      Stage 1: Detect & autonomously fix bugs
      Stage 2: Post-fix OWASP/CWE cybersecurity scan -> SECURE / INSECURE verdict
    """
    from core.repo_executor import OnDemandRepoExecutor
    try:
        body = await request.json()
        target = str(body.get("target", "")).strip()
    except Exception:
        return JSONResponse({"status": "error", "error": "Invalid JSON payload."}, status_code=400)

    if not target:
        return JSONResponse(
            {"status": "error", "error": "Please provide a GitHub repository URL or local folder path."},
            status_code=400
        )

    executor = OnDemandRepoExecutor()
    result = await asyncio.to_thread(executor.execute, target)
    return JSONResponse(result, status_code=200 if result.get("status") == "completed" else 400)


async def api_security_audit(request):
    """On-demand OWASP Top 10 / CWE SAST scan for a provided path or pasted code snippet."""
    from core.security_scanner import SecurityVulnerabilityScanner

    scanner = SecurityVulnerabilityScanner()
    if request.method == "POST":
        try:
            body = await request.json()
        except Exception:
            body = {}
        inline_code = body.get("code")
        target_path = str(body.get("target_path", "")).strip()
        filename = str(body.get("filename", "snippet.py")).strip() or "snippet.py"

        if inline_code is not None and str(inline_code).strip():
            report = await asyncio.to_thread(scanner.scan_code, str(inline_code), filename)
            return JSONResponse(report)

        if not target_path:
            return JSONResponse(
                {"status": "error", "error": "Please provide code or target_path to audit."},
                status_code=400
            )
        report = await asyncio.to_thread(scanner.scan_directory, target_path)
        return JSONResponse(report)

    target_path = request.query_params.get("target", "").strip()
    if not target_path:
        return JSONResponse({"status": "idle", "message": "Provide ?target=<path> or POST code/target_path."})
    report = await asyncio.to_thread(scanner.scan_directory, target_path)
    return JSONResponse(report)


async def api_chat(request):
    """Process conversational engineering request through LangGraph."""
    try:
        body = await request.json()
        user_message = body.get("message", "").strip()
        thread_id = body.get("thread_id", "default_session")

        if not user_message:
            return JSONResponse({"error": "Empty message received."}, status_code=400)

        cfg = get_settings()
        api_key_set = bool(
            cfg.GOOGLE_API_KEY
            or cfg.OPENAI_API_KEY
            or cfg.ANTHROPIC_API_KEY
            or os.getenv("GOOGLE_API_KEY")
            or os.getenv("OPENAI_API_KEY")
        )

        if not api_key_set and cfg.MODEL_PROVIDER != "ollama":
            return JSONResponse({
                "reply": (
                    f"⚠️ **API Key Required**\n\n"
                    f"Add your `{cfg.MODEL_PROVIDER.upper()}` API key in `.env` and restart the server."
                ),
                "tool_calls": []
            })

        assistant = get_assistant_instance()
        if not assistant:
            from core.agent import PersonalAssistant
            assistant = PersonalAssistant()

        result = await asyncio.to_thread(assistant.chat_with_metadata, user_message, thread_id)
        return JSONResponse({
            "reply": result.get("reply", ""),
            "tool_calls": result.get("tool_calls", [])
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def api_reports(request):
    """Return historical audit reports persisted in the SQLite relational database."""
    from core.database import get_audit_db
    try:
        limit = int(request.query_params.get("limit", 15))
    except (ValueError, TypeError):
        limit = 15
    db = get_audit_db()
    reports = await asyncio.to_thread(db.get_recent_reports, limit)
    return JSONResponse(reports)


routes = [
    Route("/", homepage),
    Route("/api/status", api_status),
    Route("/api/memory", api_memory),
    Route("/api/tools", api_tools),
    Route("/api/reports", api_reports),
    Route("/api/decode_repo", api_decode_repo, methods=["POST"]),
    Route("/api/execute_repo", api_execute_repo, methods=["POST"]),
    Route("/api/security_audit", api_security_audit, methods=["GET", "POST"]),
    Route("/api/chat", api_chat, methods=["POST"]),
]

app = Starlette(debug=False, routes=routes)


def start_server(host: str = "127.0.0.1", port: int = 8000):
    """Launch the WOLF DevSecOps Web Server."""
    print("=" * 65)
    print("WOLF DevSecOps Platform starting")
    print(f"Open: http://{host}:{port}")
    print("=" * 65)
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    start_server()
