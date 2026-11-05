"""
Long-Term User Profile & Facts Memory Store.
============================================
This module manages permanent user facts, personal preferences, and long-term knowledge.
Data is persisted to disk in JSON format so it survives restarts.

WHY THIS FOLDER MATTERS:
- Modify this file if you want to swap JSON storage for SQLite, Redis, or PostgreSQL.
- The agent calls this store to remember user preferences across sessions.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from config.settings import get_settings


class UserProfileStore:
    """Manages persistent long-term key-value facts about the user."""

    def __init__(self, storage_path: Optional[str] = None):
        cfg = get_settings()
        self.file_path = Path(storage_path or cfg.USER_FACTS_FILE)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_file()

    def _ensure_file(self) -> None:
        """Create the facts file with default JSON if not present."""
        if not self.file_path.exists():
            initial_data = {
                "user_name": get_settings().DEFAULT_USER_NAME,
                "notes": "Initialized assistant memory."
            }
            self._write(initial_data)

    def _read(self) -> Dict[str, Any]:
        """Read all facts from file."""
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _write(self, data: Dict[str, Any]) -> None:
        """Write facts dictionary to file."""
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_all_facts(self) -> Dict[str, Any]:
        """Retrieve all currently remembered facts."""
        return self._read()

    def get_fact(self, key: str, default: Any = None) -> Any:
        """Get a specific fact by key."""
        facts = self._read()
        return facts.get(key, default)

    def set_fact(self, key: str, value: Any) -> str:
        """
        Save or update a fact in permanent memory.
        Returns confirmation string.
        """
        facts = self._read()
        facts[key] = value
        self._write(facts)
        return f"Successfully remembered '{key}': {value}"

    def delete_fact(self, key: str) -> bool:
        """Remove a fact from memory."""
        facts = self._read()
        if key in facts:
            del facts[key]
            self._write(facts)
            return True
        return False

    def clear(self) -> None:
        """Wipe all stored facts."""
        self._write({})


_user_store: Optional[UserProfileStore] = None

def get_user_store() -> UserProfileStore:
    """Singleton accessor for the user profile store."""
    global _user_store
    if _user_store is None:
        _user_store = UserProfileStore()
    return _user_store

