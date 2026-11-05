"""
Settings and Environment Configuration Module.
==============================================
This module handles all application settings, loading configuration from 
environment variables and `.env` files using Pydantic Settings.

WHY THIS FOLDER MATTERS:
- Modify this file if you want to change default timeouts, paths, model choices, 
  or add new configuration parameters (e.g. database credentials, API endpoints).
- NEVER hardcode secrets or model names in `main.py`.
"""

import os
from pathlib import Path
from typing import Literal, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the Personal AI Assistant."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # -------------------------------------------------------------
    # 1. Model Provider Configuration (Model-Agnostic)
    # -------------------------------------------------------------
    MODEL_PROVIDER: Literal["gemini", "openai", "anthropic", "ollama"] = Field(
        default="gemini",
        description="The AI model provider to use (gemini, openai, anthropic, ollama)"
    )
    MODEL_NAME: str = Field(
        default="gemini-flash-lite-latest",
        description="Specific model identifier (e.g. gemini-flash-lite-latest, gpt-4o-mini, claude-3-5-sonnet)"
    )
    TEMPERATURE: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature for the LLM (0.0 = deterministic, 1.0 = creative)"
    )
    MAX_TOKENS: int = Field(
        default=2048,
        description="Maximum tokens generated per response"
    )

    # -------------------------------------------------------------
    # 2. Provider API Credentials
    # -------------------------------------------------------------
    GOOGLE_API_KEY: Optional[str] = Field(default=None, description="Google Gemini API Key")
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API Key")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, description="Anthropic API Key")
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434", description="Base URL for local Ollama")

    # -------------------------------------------------------------
    # 3. Agent Persona & Context
    # -------------------------------------------------------------
    AGENT_NAME: str = Field(default="Nexus", description="Name of the AI Assistant")
    DEFAULT_USER_NAME: str = Field(default="User", description="Default user name if not identified")
    
    # -------------------------------------------------------------
    # 4. Memory & Context Window Settings
    # -------------------------------------------------------------
    MAX_HISTORY_MESSAGES: int = Field(
        default=16,
        description="Maximum recent messages to feed to LLM context before trimming"
    )
    STORAGE_DIR: Path = Field(
        default=Path("./data"),
        description="Directory where persistent memory and checkpoints are saved"
    )
    DATABASE_FILE: str = Field(
        default="./data/agent_memory.db",
        description="SQLite database file path for session history persistence"
    )
    USER_FACTS_FILE: str = Field(
        default="./data/user_profile.json",
        description="JSON store for long-term user facts and semantic memory"
    )

    def ensure_directories(self) -> None:
        """Create necessary storage directories if they do not exist."""
        self.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        db_parent = Path(self.DATABASE_FILE).parent
        db_parent.mkdir(parents=True, exist_ok=True)


# Global cached settings instance
_settings: Optional[Settings] = None

def get_settings() -> Settings:
    """Singleton getter for application settings."""
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.ensure_directories()
    return _settings

