"""
Central Tool Registry.
======================
This module acts as the single source of truth for all tools available to the agent.
It decouples tool creation from agent execution and merges:
1. Native local tools (Weather, Web Search, Calculator, Notes, Memory).
2. Dynamically loaded tools from multiple MCP (Model Context Protocol) servers.

HOW TO ADD A NEW TOOL:
1. Native Tool: Create in `tools/my_tool.py`, decorate with `@tool`, add to `_NATIVE_TOOLS`.
2. MCP Server: Just register the server in `config/mcp_servers.json`!
"""

from typing import List
from langchain_core.tools import BaseTool

# Import all individual native tools
from tools.weather_tool import get_weather
from tools.calculator_tool import calculate
from tools.memory_tool import remember_user_fact, get_user_facts
from tools.notes_tool import save_note, list_notes

# Import MCP Multi-Server tool loader
from mcp_service.manager import get_mcp_tools_sync
from utils.logger import setup_logger

logger = setup_logger("tool_registry")

# Initial native registered tools (System, Math, GitHub & Web Search are loaded via MCP)
_NATIVE_TOOLS: List[BaseTool] = [
    get_weather,
    calculate,
    remember_user_fact,
    get_user_facts,
    save_note,
    list_notes
]


def get_all_tools(include_mcp: bool = True) -> List[BaseTool]:
    """
    Retrieve all tools: both native tools and tools loaded across all
    active Model Context Protocol (MCP) servers.
    """
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
