"""
Checkpointer & Session History Persistence Module.
==================================================
This module provides checkpointers for saving state and conversation threads.
It allows the agent to maintain multiple separate conversation threads (sessions)
without state leakage.

WHY THIS FOLDER MATTERS:
- Modify this file if you want to switch checkpointing backends (e.g. PostgresSaver,
  RedisSaver, SQLiteSaver, or In-Memory).
"""

from typing import Optional
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.base import BaseCheckpointSaver
from config.settings import get_settings


_checkpointer_instance: Optional[BaseCheckpointSaver] = None

def get_checkpointer() -> BaseCheckpointSaver:
    """
    Returns a checkpointer instance for state management.
    Defaults to MemorySaver for fast thread-isolated persistence.
    Can be swapped to SqliteSaver or PostgresSaver seamlessly.
    """
    global _checkpointer_instance
    if _checkpointer_instance is None:
        # Standard MemorySaver handles multi-session conversation checkpointing
        _checkpointer_instance = MemorySaver()
    return _checkpointer_instance

