"""
Multi-MCP Server Lifecycle & Tool Manager.
==========================================
Manages connections to multiple MCP servers concurrently and adapts their tools
into standard LangChain BaseTool instances for the AI Agent.

WHY THIS FOLDER MATTERS:
- Modify this file if you want custom authentication, telemetry, or specialized
  transports for your MCP connections.
- Everything here conforms to the official Model Context Protocol (MCP) standard.
"""

import asyncio
import concurrent.futures
from typing import List, Dict, Any, Optional
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from mcp_service.config import load_mcp_server_configs
from utils.logger import setup_logger

logger = setup_logger("mcp_manager")


class MCPManager:
    """Manages multi-server MCP connections and tool discovery."""

    def __init__(self, server_configs: Optional[Dict[str, Dict[str, Any]]] = None):
        self.configs = server_configs if server_configs is not None else load_mcp_server_configs()
        self.client: Optional[MultiServerMCPClient] = None
        self._cached_tools: List[BaseTool] = []

    async def initialize(self) -> List[BaseTool]:
        """
        Connects to all enabled MCP servers and loads their tools.
        Returns a list of LangChain-compatible tools.
        """
        if not self.configs:
            logger.info("No active MCP servers found in configuration.")
            return []

        connection_dict = {}
        for server_name, cfg in self.configs.items():
            transport = cfg.get("transport", "stdio")
            if transport == "stdio":
                connection_dict[server_name] = {
                    "transport": "stdio",
                    "command": cfg["command"],
                    "args": cfg.get("args", [])
                }
            elif transport == "sse":
                connection_dict[server_name] = {
                    "transport": "sse",
                    "url": cfg.get("url")
                }

        try:
            logger.info(f"Connecting to {len(connection_dict)} MCP servers: {list(connection_dict.keys())}...")
            self.client = MultiServerMCPClient(connection_dict)
            raw_tools = await self.client.get_tools()

            # Ensure all MCP tools can be invoked synchronously by LangGraph ToolNode
            for tool in raw_tools:
                if getattr(tool, "func", None) is None and getattr(tool, "coroutine", None) is not None:
                    coro_fn = tool.coroutine
                    def make_sync(fn):
                        def sync_wrapper(*args, **kwargs):
                            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                                return ex.submit(asyncio.run, fn(*args, **kwargs)).result()
                        return sync_wrapper
                    tool.func = make_sync(coro_fn)

            self._cached_tools = raw_tools
            logger.info(f"Successfully loaded {len(self._cached_tools)} tools from MCP servers.")
            return self._cached_tools
        except Exception as e:
            logger.error(f"Error initializing MCP connections: {e}")
            return []

    def get_tools_sync(self) -> List[BaseTool]:
        """
        Thread-safe synchronous wrapper to retrieve MCP tools.
        Avoids event loop collisions when called inside Starlette / FastAPI / Uvicorn.
        """
        try:
            # Check if an event loop is already running in current thread
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None:
            # An event loop is running (e.g. inside web server). Run in a separate worker thread.
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(asyncio.run, self.initialize())
                return future.result()
        else:
            # No event loop running, safe to use standard asyncio.run
            return asyncio.run(self.initialize())


_global_manager: Optional[MCPManager] = None

def get_mcp_tools_sync() -> List[BaseTool]:
    """Retrieves all MCP tools from the singleton manager."""
    global _global_manager
    if _global_manager is None:
        _global_manager = MCPManager()
    return _global_manager.get_tools_sync()
