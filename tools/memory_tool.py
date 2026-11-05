"""
Long-Term Memory Tools.
=======================
Tools that allow the LLM to explicitly save and retrieve permanent user facts
using the UserProfileStore.

WHY THIS FOLDER MATTERS:
- Modify this file if you want to customize how the agent interacts with long-term memory.
"""

from langchain_core.tools import tool
from memory.user_profile_store import get_user_store


@tool
def remember_user_fact(fact_key: str, fact_value: str) -> str:
    """
    Save or update a persistent fact about the user into long-term memory.
    Use this whenever the user shares a personal detail, preference, background,
    or instruction they want remembered across sessions.

    Args:
        fact_key: Short descriptor for the fact (e.g. 'favorite_language', 'location', 'hobby', 'pet').
        fact_value: The detail to remember (e.g. 'Python', 'San Francisco', 'Playing guitar', 'Dog named Bruno').

    Returns:
        Confirmation message that the fact has been saved to permanent storage.
    """
    store = get_user_store()
    return store.set_fact(fact_key, fact_value)


@tool
def get_user_facts() -> str:
    """
    Retrieve all permanent facts stored about the user in long-term memory.

    Returns:
        A list of remembered facts about the user.
    """
    store = get_user_store()
    facts = store.get_all_facts()
    if not facts:
        return "No permanent user facts found in memory."
    
    lines = [f"- {k}: {v}" for k, v in facts.items()]
    return "Stored User Facts:\n" + "\n".join(lines)

