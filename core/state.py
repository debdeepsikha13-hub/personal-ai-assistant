"""
Agent State Schema Definition.
==============================
Defines the schema for the agent's internal state using TypedDict and LangGraph annotations.

WHY THIS FOLDER MATTERS:
- Modify this file if you want to add new fields to the agent's cognitive state
  (e.g., active task plan, user emotion, citation sources, or security clearances).
"""

from typing import Annotated, Sequence, Dict, Any, Optional
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    The complete state schema passed between nodes in the agent graph.
    
    Attributes:
        messages: List of conversation messages (User, Assistant, System, Tool).
                  Using `add_messages` automatically appends new messages.
        user_facts: Persistent user facts injected into the conversation.
        context_summary: Optional running summary of long past conversations.
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_facts: Optional[Dict[str, Any]]
    context_summary: Optional[str]

