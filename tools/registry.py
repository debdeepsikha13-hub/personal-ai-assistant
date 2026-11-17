"""
Central Tool Registry.
======================
Single source of truth for WOLF's DevSecOps engineering tools:
  1. Native Engineering & Security Tools (On-Demand Repo Executor, Bug Fixer, OWASP/CWE SAST Scanner, Memory)
  2. MCP Microservices (Groq Technical/CVE Search, Read-Only GitHub)
"""

from typing import List
from langchain_core.tools import BaseTool

# 1. On-Demand Bug Remediation & Cybersecurity SAST Tools
from tools.bug_fixer_tool import execute_repository_link, run_bug_fixer_agent, run_code_quality_checklist
from tools.security_tool import run_security_audit

# 2. Persistent Engineering Context Memory
from tools.memory_tool import remember_user_fact, get_user_facts

# 3. MCP Tool Loader (Groq Technical Search & Read-Only GitHub)
from mcp_service.manager import get_mcp_tools_sync
from utils.logger import setup_logger

logger = setup_logger("tool_registry")

_NATIVE_TOOLS: List[BaseTool] = [
    execute_repository_link,
    run_bug_fixer_agent,
    run_code_quality_checklist,
    run_security_audit,
    remember_user_fact,
    get_user_facts,
]


def get_all_tools(include_mcp: bool = True) -> List[BaseTool]:
    """Retrieve all native DevSecOps tools plus active MCP microservice tools."""
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
