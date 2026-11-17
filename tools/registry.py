"""
Central Tool Registry.
======================
Single source of truth for all tools available to WOLF:
  1. Native Engineering & Security Tools (On-Demand Repo Executor, Bug Fixer, OWASP/CWE SAST Scanner)
  2. Native Assistant Tools (Weather, Calculator, Notes, Long-Term Memory)
  3. MCP Microservices (PC Specs / System Diagnostics, Advanced Math, Read-Only GitHub, Groq Tech Search)
"""

from typing import List
from langchain_core.tools import BaseTool

# 1. On-Demand Bug Remediation & Cybersecurity SAST Tools
from tools.bug_fixer_tool import execute_repository_link, run_bug_fixer_agent, run_code_quality_checklist
from tools.security_tool import run_security_audit

# 2. Assistant Utility & Memory Tools
from tools.weather_tool import get_weather
from tools.calculator_tool import calculate
from tools.notes_tool import save_note, list_notes
from tools.memory_tool import remember_user_fact, get_user_facts

# 3. MCP Multi-Server Tool Loader (System Diagnostics, Advanced Math, GitHub, Groq Web Search)
from mcp_service.manager import get_mcp_tools_sync
from utils.logger import setup_logger

logger = setup_logger("tool_registry")

_NATIVE_TOOLS: List[BaseTool] = [
    # DevSecOps: On-Demand Bug Fixer & Security Scanner
    execute_repository_link,
    run_bug_fixer_agent,
    run_code_quality_checklist,
    run_security_audit,
    # Utilities & Memory
    get_weather,
    calculate,
    save_note,
    list_notes,
    remember_user_fact,
    get_user_facts,
]


def get_all_tools(include_mcp: bool = True) -> List[BaseTool]:
    """Retrieve all native tools plus all active MCP microservice tools."""
    combined = list(_NATIVE_TOOLS)
    if include_mcp:
        try:
            mcp_tools = get_mcp_tools_sync()
            combined.extend(mcp_tools)
        except Exception as e:
            logger.warning(f"Could not load MCP tools: {e}")
    return combined


def register_tool(tool_instance: BaseTool) -> None:
    """Dynamically register an additional native tool at runtime."""
    if tool_instance not in _NATIVE_TOOLS:
        _NATIVE_TOOLS.append(tool_instance)
