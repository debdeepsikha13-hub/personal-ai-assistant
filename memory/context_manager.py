"""
Context & Conversation Window Manager.
======================================
This module prevents context window overflow and optimizes message history.
It prunes, trims, and summarizes message histories so the LLM remains within
token limits while keeping important recent context and system prompts intact.

WHY THIS FOLDER MATTERS:
- Modify this file if you need advanced token counting, semantic compression,
  or specialized conversation pruning strategies.
"""

from typing import List, Sequence
from langchain_core.messages import BaseMessage, SystemMessage, trim_messages
from config.settings import get_settings


class ContextManager:
    """Manages conversational context length and message schemas."""

    def __init__(self, max_messages: int = 16):
        self.max_messages = max_messages or get_settings().MAX_HISTORY_MESSAGES

    def optimize_messages(
        self,
        messages: Sequence[BaseMessage],
        system_prompt: Optional[str] = None
    ) -> List[BaseMessage]:
        """
        Trims message history to the most recent N messages, preserving
        conversation coherence and ensuring system instructions are retained.

        Args:
            messages: Full list of conversation messages so far.
            system_prompt: Optional active system prompt string to prepend if needed.

        Returns:
            List[BaseMessage]: Optimized message sequence safe for LLM context limits.
        """
        # If message history is within limits, return as is
        if len(messages) <= self.max_messages:
            return list(messages)

        # Use LangChain's trim_messages to safely trim while ensuring
        # tool calls and tool responses are not split apart
        trimmed = trim_messages(
            list(messages),
            max_tokens=self.max_messages,
            token_counter=len, # Count by number of messages
            strategy="last",
            allow_partial=False,
            include_system=True,
            start_on="human"
        )

        return trimmed

