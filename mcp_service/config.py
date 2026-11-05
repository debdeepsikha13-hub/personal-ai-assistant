"""
MCP Server Configuration Loader.
================================
Loads, parses, and validates the MCP server definitions from config/mcp_servers.json.

WHY THIS FOLDER MATTERS:
- Modify config/mcp_servers.json whenever you want to plug in external MCP servers
  (like GitHub MCP, SQLite MCP, Fetch MCP, Brave MCP, etc.).
- No code changes required!
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any


def get_mcp_config_path() -> Path:
    """Returns the path to the mcp_servers.json file."""
    return Path(__file__).parent.parent / "config" / "mcp_servers.json"


def load_mcp_server_configs() -> Dict[str, Dict[str, Any]]:
    """
    Reads config/mcp_servers.json and returns a dictionary of active MCP server configurations.
    Automatically resolves virtual environment python path if specified.
    """
    config_file = get_mcp_config_path()
    if not config_file.exists():
        return {}

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        servers = data.get("mcpServers", {})
        active_servers = {}

        base_dir = config_file.parent.parent

        for name, s_cfg in servers.items():
            if not s_cfg.get("enabled", True):
                continue

            command = s_cfg.get("command", "")
            # If command refers to virtual environment python, resolve to actual running python
            if "python" in command.lower():
                command = sys.executable

            args = []
            for a in s_cfg.get("args", []):
                # If arg refers to a local file, resolve relative to project root
                arg_path = base_dir / a
                if arg_path.exists():
                    args.append(str(arg_path))
                else:
                    args.append(a)

            transport = s_cfg.get("transport", "stdio")

            active_servers[name] = {
                "transport": transport,
                "command": command,
                "args": args,
                "description": s_cfg.get("description", f"MCP Server: {name}"),
                "url": s_cfg.get("url") # for SSE if present
            }

        return active_servers

    except Exception as e:
        print(f"Warning: Failed to load mcp_servers.json: {e}")
        return {}
