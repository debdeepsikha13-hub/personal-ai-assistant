"""
High-Level Personal Assistant Orchestrator.
===========================================
Wraps the compiled StateGraph, LLM, Tools, and Memory into an easy-to-use
object interface for the CLI, web app, or API.

WHY THIS FOLDER MATTERS:
- Modify this file if you want to add batch execution, telemetry hooks,
  multi-user routing, or conversation reset methods.
- Keeps `main.py` ultra-simple and clean!
"""

import uuid
from typing import Dict, Any, Optional
from langchain_core.messages import HumanMessage

from config.settings import get_settings
from llm.factory import get_chat_model
from tools.registry import get_all_tools
from memory.context_manager import ContextManager
from memory.user_profile_store import get_user_store
from core.graph import create_agent_graph


class PersonalAssistant:
    """The central agent orchestrator."""

    def __init__(self, thread_id: Optional[str] = None):
        self.settings = get_settings()
        self.thread_id = thread_id or f"session_{uuid.uuid4().hex[:8]}"
        self.user_store = get_user_store()
        self.context_manager = ContextManager(max_messages=self.settings.MAX_HISTORY_MESSAGES)

        # 1. Initialize Model-Agnostic LLM
        self.model = get_chat_model(self.settings)

        # 2. Collect Registered Tools
        self.tools = get_all_tools()

        # 3. Assemble and compile the Graph with checkpointer
        self.graph = create_agent_graph(
            model=self.model,
            tools=self.tools,
            context_manager=self.context_manager
        )

    def chat(self, user_message: str, thread_id: Optional[str] = None) -> str:
        """
        Send a message to the agent and receive the final text response.
        Maintains conversational thread state automatically.

        Args:
            user_message: The text prompt from the user.
            thread_id: Optional session ID override.

        Returns:
            str: The assistant's final response string.
        """
        result = self.chat_with_metadata(user_message, thread_id=thread_id)
        return result["reply"]

    def chat_with_metadata(self, user_message: str, thread_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process chat and return both the text reply and any executed tool calls.
        """
        active_thread = thread_id or self.thread_id
        config = {"configurable": {"thread_id": active_thread}}
        initial_state = {
            "messages": [HumanMessage(content=user_message)]
        }

        # Run through the StateGraph (LLM -> Tools -> LLM -> Response)
        final_state = self.graph.invoke(initial_state, config=config)

        # Collect any executed tool calls from the message history of this turn
        executed_tools = []
        for msg in final_state["messages"]:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    executed_tools.append({
                        "name": tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", str(tc)),
                        "args": tc.get("args") if isinstance(tc, dict) else getattr(tc, "args", {})
                    })

        # The last message is the Assistant's final response
        last_message = final_state["messages"][-1]
        content = last_message.content

        # Handle list of content blocks if returned by multimodal/newer models
        if isinstance(content, list):
            text_parts = []
            for block in content:
                if isinstance(block, dict) and "text" in block:
                    text_parts.append(block["text"])
                elif isinstance(block, str):
                    text_parts.append(block)
                elif hasattr(block, "text"):
                    text_parts.append(getattr(block, "text"))
                else:
                    text_parts.append(str(block))
            reply = "\n".join(text_parts)
        else:
            reply = str(content)

        return {
            "reply": reply,
            "tool_calls": executed_tools
        }

    def get_user_facts(self) -> Dict[str, Any]:
        """Inspect all permanent memories currently stored for the user."""
        return self.user_store.get_all_facts()

    def set_user_fact(self, key: str, value: str) -> str:
        """Manually store or update a permanent user fact."""
        return self.user_store.set_fact(key, value)

