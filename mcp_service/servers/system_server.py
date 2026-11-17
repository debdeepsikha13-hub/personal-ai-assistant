"""
System Information MCP Server.
==============================
A standalone Model Context Protocol (MCP) server that provides system diagnostics,
OS specs, hardware info, and file directory inspection over stdio.

HOW THIS WORKS (MCP):
- This server communicates with any MCP client (like our Agent, Claude, or Cursor)
  using standard JSON-RPC over stdin/stdout.
- It exposes tools using the FastMCP decorator.
"""

import os
import sys
import platform
import shutil
from pathlib import Path
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP Server
mcp = FastMCP("SystemDiagnosticsServer")


@mcp.tool()
def get_system_specs() -> str:
    """
    Get detailed operating system and machine hardware specifications.
    
    Returns:
        Formatted summary of OS version, CPU architecture, Python version, and machine name.
    """
    specs = {
        "OS": platform.system(),
        "OS Release": platform.release(),
        "OS Version": platform.version(),
        "Architecture": platform.machine(),
        "Processor": platform.processor(),
        "Python Version": sys.version.split()[0],
        "Machine Name": platform.node()
    }
    lines = [f"- **{k}**: {v}" for k, v in specs.items()]
    return "System Specifications:\n" + "\n".join(lines)


@mcp.tool()
def get_disk_usage(path: str = ".") -> str:
    """
    Check the total, used, and free disk space for a given folder or drive.
    
    Args:
        path: Directory path or drive letter (e.g. '.' or 'C:\\').
        
    Returns:
        Disk capacity statistics in Gigabytes (GB).
    """
    try:
        total, used, free = shutil.disk_usage(path)
        gb = 1024 ** 3
        return (
            f"Disk Usage for '{path}':\n"
            f"- Total Space: {total / gb:.2f} GB\n"
            f"- Used Space:  {used / gb:.2f} GB\n"
            f"- Free Space:  {free / gb:.2f} GB\n"
            f"- Percent Free: {(free / total) * 100:.1f}%"
        )
    except Exception as e:
        return f"Error reading disk usage for '{path}': {str(e)}"


@mcp.tool()
def list_directory(directory_path: str = ".") -> str:
    """
    List files and folders in a specified local directory.
    
    Args:
        directory_path: Directory path to inspect (defaults to current folder).
        
    Returns:
        List of files and directories.
    """
    try:
        p = Path(directory_path)
        if not p.exists():
            return f"Path does not exist: {directory_path}"
        
        items = list(p.iterdir())[:30] # Limit to 30 items for brevity
        lines = []
        for item in items:
            kind = "[DIR] " if item.is_dir() else "[FILE]"
            lines.append(f"{kind} {item.name}")
            
        return f"Directory contents of '{directory_path}' ({len(items)} items):\n" + "\n".join(lines)
    except Exception as e:
        return f"Error listing directory '{directory_path}': {str(e)}"


if __name__ == "__main__":
    # Start stdio transport
    mcp.run(transport="stdio")
