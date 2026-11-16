"""
Model-Agnostic LLM Factory Module.
===================================
This module provides a unified factory function to instantiate any LLM provider
(Google Gemini, OpenAI, Anthropic Claude, or local Ollama) based on settings.

WHY THIS FOLDER MATTERS:
- Modify this file if you want to switch LLMs or add new providers (e.g. Groq, Cohere, Bedrock).
- The rest of the agent code ONLY talks to standard LangChain `BaseChatModel`.
- You never have to touch `main.py` or `core/` to change or tweak a model!
"""

import os
from typing import Optional
from langchain_core.language_models.chat_models import BaseChatModel
from config.settings import Settings, get_settings


def get_chat_model(settings: Optional[Settings] = None) -> BaseChatModel:
    """
    Factory function returning a configured LangChain ChatModel instance.
    
    Supports:
      - 'gemini'    -> Google Gemini (e.g., gemini-2.0-flash, gemini-1.5-flash)
      - 'openai'    -> OpenAI (e.g., gpt-4o-mini, gpt-4o)
      - 'anthropic' -> Anthropic Claude (e.g., claude-3-5-sonnet)
      - 'ollama'    -> Local Ollama (e.g., llama3.2, mistral)

    Args:
        settings: Application Settings object (falls back to singleton if None)

    Returns:
        BaseChatModel: An initialized, tool-calling capable LangChain chat model.
    """
    cfg = settings or get_settings()
    provider = cfg.MODEL_PROVIDER.lower().strip()
    model_name = cfg.MODEL_NAME.strip()
    temperature = cfg.TEMPERATURE
    max_tokens = cfg.MAX_TOKENS

    if provider == "gemini":
        api_key = cfg.GOOGLE_API_KEY or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "Missing GOOGLE_API_KEY! Please set it in your .env file or "
                "switch MODEL_PROVIDER to 'ollama' or 'openai'."
            )
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError:
            raise ImportError("Please install langchain-google-genai via pip.")

        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=temperature,
            max_output_tokens=max_tokens,
            max_retries=1,
            convert_system_message_to_human=False
        )

    elif provider == "groq":
        api_key = cfg.GROQ_API_KEY or os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError(
                "Missing GROQ_API_KEY! Please set it in your .env file."
            )
        try:
            from langchain_groq import ChatGroq
        except ImportError:
            raise ImportError("Please install langchain-groq via pip.")

        return ChatGroq(
            model_name=model_name if "llama" in model_name.lower() or "mixtral" in model_name.lower() else "llama-3.3-70b-versatile",
            groq_api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens
        )

    elif provider == "openai":
        api_key = cfg.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "Missing OPENAI_API_KEY! Please set it in your .env file."
            )
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            raise ImportError("Please install langchain-openai via pip.")

        return ChatOpenAI(
            model=model_name,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens
        )

    elif provider == "anthropic":
        api_key = cfg.ANTHROPIC_API_KEY or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "Missing ANTHROPIC_API_KEY! Please set it in your .env file."
            )
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError:
            raise ImportError("Please install langchain-anthropic via pip.")

        return ChatAnthropic(
            model_name=model_name,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens
        )

    elif provider == "ollama":
        try:
            from langchain_community.chat_models import ChatOllama
        except ImportError:
            try:
                from langchain_ollama import ChatOllama
            except ImportError:
                raise ImportError("Please install langchain-ollama or langchain-community.")

        return ChatOllama(
            model=model_name,
            base_url=cfg.OLLAMA_BASE_URL,
            temperature=temperature
        )

    else:
        raise ValueError(
            f"Unsupported MODEL_PROVIDER '{provider}'. "
            f"Supported providers: 'gemini', 'openai', 'anthropic', 'ollama'."
        )

