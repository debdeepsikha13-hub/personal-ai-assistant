"""
Terminal User Interface and Output Formatting.
==============================================
Provides rich colored banners, markdown rendering, and status displays for the CLI.
Configured safely for cross-platform terminals (including Windows UTF-8 encoding).
"""

import sys
from typing import Dict, Any, List

# Ensure Windows terminal supports UTF-8
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.table import Table
    # legacy_windows=False avoids cp1252 character map issues on Windows
    console = Console(legacy_windows=False)
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    console = None


def print_banner(agent_name: str, model_provider: str, model_name: str) -> None:
    """Prints a clean welcome banner in the terminal."""
    capitalized_name = agent_name.capitalize()
    if HAS_RICH and console:
        banner_text = (
            f"[bold cyan]{capitalized_name} CLI[/bold cyan] [dim]• Personal Assistant[/dim]\n\n"
            f"• [green]Model:[/green] {model_name} ({model_provider.upper()})\n"
            f"• [green]Memory:[/green] Active (Checkpoints & User Profile)\n"
            f"• [yellow]Commands:[/yellow] Type [bold]'tools'[/bold] for list, [bold]'memory'[/bold] for saved facts, [bold]'exit'[/bold] to quit."
        )
        console.print(Panel(banner_text, border_style="cyan", expand=False))
    else:
        print("=" * 60)
        print(f"{capitalized_name} CLI - Personal Assistant")
        print(f"Model: {model_name} ({model_provider})")
        print("Commands: 'tools' for tools, 'memory' for facts, 'exit' to quit.")
        print("=" * 60)


def print_agent_reply(agent_name: str, reply: str) -> None:
    """Formats and prints the agent's markdown response."""
    capitalized_name = agent_name.capitalize()
    if HAS_RICH and console:
        console.print(f"\n[bold green]{capitalized_name}:[/bold green]")
        console.print(Markdown(reply))
        console.print()
    else:
        print(f"\n{capitalized_name}:\n{reply}\n")


def print_user_prompt(user_name: str) -> str:
    """Prints user prompt line."""
    return input(f"\nYou > ")


def print_system_info(title: str, content: str) -> None:
    """Prints a highlighted system notice or info block."""
    if HAS_RICH and console:
        console.print(Panel(content, title=title, border_style="blue", expand=False))
    else:
        print(f"\n--- {title} ---")
        print(content)
        print("-" * (len(title) + 8))


def print_tools_table(tools: List[Any]) -> None:
    """Displays all available tools in a clean table."""
    if HAS_RICH and console:
        table = Table(title="[Tools] Registered Agent Capabilities", border_style="magenta")
        table.add_column("Tool Name", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")
        for t in tools:
            desc = t.description.split("\n")[0] if hasattr(t, "description") else str(t)
            table.add_row(t.name if hasattr(t, "name") else str(t), desc)
        console.print(table)
    else:
        print("\nRegistered Tools:")
        for t in tools:
            name = getattr(t, "name", str(t))
            desc = getattr(t, "description", "").split("\n")[0]
            print(f"- {name}: {desc}")

