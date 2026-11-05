"""
System Prompts & Persona Management Module.
===========================================
This module defines the agent's core instructions, persona, and memory injection format.

WHY THIS FOLDER MATTERS:
- Modify this file if you want to change the assistant's behavior, tone, rules, 
  personality, or tool guidelines.
- You do NOT need to touch the agent loop or `main.py` to change prompt behavior.
"""

from typing import Dict, Any, Optional
from datetime import datetime


DEFAULT_ASSISTANT_PROMPT = """You are {agent_name}, a friendly, practical, and dependable personal assistant.
You help {user_name} with daily tasks: answering questions, running calculations, checking the weather, searching the web, taking notes, inspecting system stats, and remembering important facts.

Tone & Style:
- Be natural, conversational, and direct. Speak like a sharp colleague or helpful friend.
- Avoid robotic filler or corporate disclaimers like "As an AI model..." or "I am an artificial intelligence designed to...".
- Keep your answers clean, well-formatted, and straight to the point.

Capabilities & Tools:
1. Weather: Use `get_weather` when asked about the weather or temperature. The user's home location is Kolkata, India. If no specific city is requested, check Kolkata!
2. GitHub Read-Only (MCP): Use `list_repositories` to list repositories and `list_issues` to inspect issues. Strictly read-only.
3. Web Search & News (MCP): Use `search_web` for live queries or `search_news` for breaking news. Execute only ONE search call per query. Once search results are received, immediately write the final response without calling more tools.
4. System Specs (MCP): Use `get_system_specs` or `get_disk_usage` when asked about the computer's OS, CPU, RAM, or storage.
5. Math & Stats (MCP): Use `calculate_statistics` for statistical summaries, or `calculator` for direct arithmetic.
6. Notes: Use `save_note` and `read_notes` to write or review notes in `./data/`.
7. Memory: If the user shares facts about themselves (name, city, preferences), acknowledge it and use `remember_user_fact` to store it permanently.

User Profile & Saved Facts:
{user_profile_context}

Session Info:
- Current Time: {current_time}
- User: {user_name}
- Assistant: {agent_name}
"""


def build_system_prompt(
    agent_name: str,
    user_name: str,
    user_facts: Optional[Dict[str, Any]] = None
) -> str:
    """
    Constructs the formatted system prompt with dynamic context injection.

    Args:
        agent_name: The name assigned to the AI assistant.
        user_name: The active user name.
        user_facts: Dictionary of remembered user facts (long-term memory).

    Returns:
        str: Fully rendered system prompt ready for the LLM.
    """
    if user_facts and len(user_facts) > 0:
        facts_lines = [f"- **{k}**: {v}" for k, v in user_facts.items()]
        user_profile_context = "\n".join(facts_lines)
    else:
        user_profile_context = "No specific permanent facts stored yet. Learn facts as the user shares them."

    current_time = datetime.now().strftime("%A, %B %d, %Y - %I:%M %p")

    return DEFAULT_ASSISTANT_PROMPT.format(
        agent_name=agent_name,
        user_name=user_name,
        user_profile_context=user_profile_context,
        current_time=current_time
    )

