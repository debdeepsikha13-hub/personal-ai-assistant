"""
Web Application Server for the Personal AI Assistant.
=====================================================
Built with Starlette & Uvicorn.
Provides a REST backend and serves the interactive frontend UI.

Endpoints:
  GET  /                   -> Serves the single-page DevSecOps Studio UI
  GET  /api/status         -> Returns agent configuration and MCP server status
  GET  /api/tools          -> Lists all native and MCP tools
  GET  /api/memory         -> Returns persistent user profile facts
  GET  /api/bug_status     -> Returns live codebase AST/test status, source snapshot & SAST report
  POST /api/bug_action     -> Executes DevSecOps actions (scan, fix, full_pipeline, security_audit)
  GET  /api/security_audit -> Runs OWASP/CWE SAST cybersecurity scan on target file/repository
  POST /api/security_audit -> Runs OWASP/CWE SAST scan on custom path or inline Python source
  POST /api/chat           -> Processes conversational message via LangGraph
"""

import sys
import os
import json
import asyncio
from pathlib import Path
from typing import Dict, Any

from starlette.applications import Starlette
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route
import uvicorn

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import get_settings
from memory.user_profile_store import get_user_store
from tools.registry import get_all_tools
from mcp_service.config import load_mcp_server_configs

# Global assistant instance
_assistant = None


def get_assistant_instance():
    """Lazy initializer for the agent to avoid startup crashes if API key is missing."""
    global _assistant
    if _assistant is None:
        try:
            from core.agent import PersonalAssistant
            _assistant = PersonalAssistant()
        except Exception as e:
            # If API key is missing or model fails to load, keep None
            _assistant = None
    return _assistant


async def homepage(request):
    """Serve the single-page application HTML."""
    html_file = Path(__file__).parent / "index.html"
    if not html_file.exists():
        return HTMLResponse("<h1>Frontend index.html not found!</h1>", status_code=404)
    with open(html_file, "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content)


async def api_status(request):
    """Return backend status, active model, and MCP connections."""
    cfg = get_settings()
    mcp_configs = load_mcp_server_configs()
    store = get_user_store()
    facts = store.get_all_facts()

    has_api_key = bool(
        cfg.GOOGLE_API_KEY or 
        cfg.OPENAI_API_KEY or 
        cfg.ANTHROPIC_API_KEY or 
        os.getenv("GOOGLE_API_KEY") or 
        os.getenv("OPENAI_API_KEY")
    )

    return JSONResponse({
        "agent_name": cfg.AGENT_NAME,
        "provider": cfg.MODEL_PROVIDER,
        "model": cfg.MODEL_NAME,
        "has_api_key": has_api_key,
        "mcp_servers": len(mcp_configs),
        "facts_count": len(facts)
    })


async def api_memory(request):
    """Return current permanent facts stored in UserProfileStore."""
    store = get_user_store()
    return JSONResponse(store.get_all_facts())


async def api_tools(request):
    """Return all available tools with metadata identifying Native vs MCP."""
    from tools.registry import _NATIVE_TOOLS
    from mcp_service.manager import MCPManager

    tools_data = []

    # 1. Native tools
    for t in _NATIVE_TOOLS:
        name = getattr(t, "name", str(t))
        desc = getattr(t, "description", "")
        clean_desc = desc.strip().split("\n")[0] if desc else "No description"
        tools_data.append({
            "name": name,
            "description": clean_desc,
            "type": "native"
        })

    # 2. Async MCP tools loaded via active event loop
    try:
        mcp_mgr = MCPManager()
        mcp_tools = await mcp_mgr.initialize()
        for t in mcp_tools:
            name = getattr(t, "name", str(t))
            desc = getattr(t, "description", "")
            clean_desc = desc.strip().split("\n")[0] if desc else "MCP Tool"
            tools_data.append({
                "name": name,
                "description": clean_desc,
                "type": "mcp"
            })
    except Exception as e:
        print(f"Note: MCP tools loading in API: {e}")

    return JSONResponse(tools_data)


async def api_chat(request):
    """Process incoming chat message through the LangGraph engine."""
    try:
        body = await request.json()
        user_message = body.get("message", "").strip()
        thread_id = body.get("thread_id", "default_session")

        if not user_message:
            return JSONResponse({"error": "Empty message received"}, status_code=400)

        cfg = get_settings()
        api_key_set = bool(
            cfg.GOOGLE_API_KEY or 
            cfg.OPENAI_API_KEY or 
            cfg.ANTHROPIC_API_KEY or 
            os.getenv("GOOGLE_API_KEY") or 
            os.getenv("OPENAI_API_KEY")
        )

        # Fallback guidance if API key is not yet configured in .env
        if not api_key_set and cfg.MODEL_PROVIDER != "ollama":
            return JSONResponse({
                "reply": (
                    f"⚠️ **API Key Required for Live Autonomous Chatting**\n\n"
                    f"I detected that your `.env` file does not have an API key set for **{cfg.MODEL_PROVIDER.upper()}** yet.\n\n"
                    f"### How to activate full chatting in 30 seconds:\n"
                    f"1. Open the `.env` file in the project folder.\n"
                    f"2. Paste your Google Gemini API key: `GOOGLE_API_KEY=AIzaSy...`\n"
                    f"3. Refresh this page and ask me anything!\n\n"
                    f"*(Tip: To get a 100% free key, visit [Google AI Studio](https://aistudio.google.com/app/apikey).)*"
                ),
                "tool_calls": []
            })

        # Process through full LangGraph Agent in worker thread
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


async def api_bug_status(request):
    """Return live codebase status, active bugs, test checklist matrix, source snapshot, and SAST report."""
    from core.bug_fixer_agent import GeneralCodeBugFixerAgent
    target_path = request.query_params.get("target", "").strip() or None
    agent = GeneralCodeBugFixerAgent(target_path=target_path)
    scan = await asyncio.to_thread(agent.scan_for_bugs)
    tests = scan["test_results"]
    security = await asyncio.to_thread(agent.run_security_audit)
    source = await asyncio.to_thread(agent.get_source_snapshot)
    return JSONResponse({
        "target": agent.target_path,
        "bug_found": scan["bug_found"],
        "diagnosis": scan.get("diagnosis"),
        "ast_issues": scan.get("ast_issues", []),
        "tests": tests,
        "security": security,
        "source": source
    })


async def api_bug_action(request):
    """Execute autonomous DevSecOps action (scan, fix, full_pipeline, security_audit)."""
    from core.bug_fixer_agent import GeneralCodeBugFixerAgent
    try:
        body = await request.json()
        action = str(body.get("action", "full_pipeline")).strip().lower()
        target_path = str(body.get("target_path", "")).strip() or None
    except Exception:
        action = "full_pipeline"
        target_path = None

    if action not in {"scan", "fix", "full_pipeline", "security_audit"}:
        return JSONResponse(
            {"error": f"Unsupported action '{action}'. Allowed: scan, fix, full_pipeline, security_audit."},
            status_code=400
        )

    agent = GeneralCodeBugFixerAgent(target_path=target_path)

    if action == "security_audit":
        res = await asyncio.to_thread(agent.run_security_audit)
        tests = await asyncio.to_thread(agent.run_tests)
        security = res
    elif action == "fix":
        res = await asyncio.to_thread(agent.apply_fix)
        tests = await asyncio.to_thread(agent.run_tests)
        security = await asyncio.to_thread(agent.run_security_audit)
    elif action == "scan":
        res = await asyncio.to_thread(agent.scan_for_bugs)
        tests = res["test_results"]
        security = await asyncio.to_thread(agent.run_security_audit)
    else:
        res = await asyncio.to_thread(agent.run_full_pipeline)
        tests = res["verification_results"]
        security = res["security_audit"]

    source = await asyncio.to_thread(agent.get_source_snapshot)
    return JSONResponse({
        "action": action,
        "target": agent.target_path,
        "result": res,
        "tests": tests,
        "security": security,
        "source": source
    })


async def api_security_audit(request):
    """Run OWASP Top 10 / CWE SAST cybersecurity scan on a repository path, file, or inline code."""
    from core.bug_fixer_agent import TARGET_FILE_PATH
    from core.security_scanner import SecurityVulnerabilityScanner

    scanner = SecurityVulnerabilityScanner()

    if request.method == "POST":
        try:
            body = await request.json()
        except Exception:
            body = {}
        inline_code = body.get("code")
        target_path = str(body.get("target_path", "")).strip() or None
        filename = str(body.get("filename", "<submitted_snippet.py>")).strip() or "<submitted_snippet.py>"

        if inline_code is not None and str(inline_code).strip():
            report = await asyncio.to_thread(scanner.scan_code, str(inline_code), filename)
            return JSONResponse(report)

        effective_target = target_path or TARGET_FILE_PATH
        report = await asyncio.to_thread(scanner.scan_directory, effective_target)
        return JSONResponse(report)

    target_path = request.query_params.get("target", "").strip() or TARGET_FILE_PATH
    report = await asyncio.to_thread(scanner.scan_directory, target_path)
    return JSONResponse(report)


# Define routes
routes = [
    Route("/", homepage),
    Route("/api/status", api_status),
    Route("/api/memory", api_memory),
    Route("/api/tools", api_tools),
    Route("/api/bug_status", api_bug_status),
    Route("/api/bug_action", api_bug_action, methods=["POST"]),
    Route("/api/security_audit", api_security_audit, methods=["GET", "POST"]),
    Route("/api/chat", api_chat, methods=["POST"]),
]

app = Starlette(debug=True, routes=routes)


def start_server(host: str = "127.0.0.1", port: int = 8000):
    """Launch the Web Application."""
    print("=" * 65)
    print("🚀 Nexus Web Application starting!")
    print(f"👉 Open your browser at: http://{host}:{port}")
    print("=" * 65)
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    start_server()
