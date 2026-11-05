"""
Personal Notes & Reminders Tool.
================================
Allows the user to store and retrieve personal notes, ideas, and reminders.
Persisted in data/notes.json.

WHY THIS FOLDER MATTERS:
- Modify this file if you want notes stored in Notion, Obsidian, or Google Keep!
"""

import json
from pathlib import Path
from datetime import datetime
from langchain_core.tools import tool
from config.settings import get_settings


def _get_notes_path() -> Path:
    cfg = get_settings()
    path = cfg.STORAGE_DIR / "notes.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with open(path, "w", encoding="utf-8") as f:
            json.dump([], f)
    return path


@tool
def save_note(title: str, content: str) -> str:
    """
    Save a new personal note or reminder with a title and content.

    Args:
        title: Short title or subject of the note.
        content: The detailed note body.

    Returns:
        Confirmation message.
    """
    path = _get_notes_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            notes = json.load(f)
    except Exception:
        notes = []

    note_entry = {
        "id": len(notes) + 1,
        "title": title,
        "content": content,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    notes.append(note_entry)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(notes, f, indent=2)

    return f"Note '{title}' saved successfully at {note_entry['timestamp']}."


@tool
def list_notes() -> str:
    """
    List all previously saved notes and reminders.

    Returns:
        A formatted list of notes or a message if empty.
    """
    path = _get_notes_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            notes = json.load(f)
    except Exception:
        return "No notes found."

    if not notes:
        return "No notes recorded yet."

    lines = ["Your Saved Notes:"]
    for n in notes:
        lines.append(f"[{n['id']}] {n['title']} ({n['timestamp']})\n    {n['content']}")

    return "\n\n".join(lines)

