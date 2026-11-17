"""
Web Search & Technical Intelligence Tool.
=========================================
Searches the web in real-time and synthesizes answers using Groq LLaMA-3.3.
"""

import os
from dotenv import load_dotenv
from langchain_core.tools import tool
from duckduckgo_search import DDGS
from typing import Optional

# Ensure environment variables are loaded
load_dotenv()


def _synthesize_with_groq(query: str, raw_results: str) -> str:
    """Synthesizes web results using Groq LLM inference if GROQ_API_KEY is available."""
    groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not groq_api_key:
        return (
            "⚠️ **Groq Search Synthesis Inactive: Missing GROQ_API_KEY**\n"
            "To enable Groq synthesis, paste your free Groq API key in `.env`:\n"
            "`GROQ_API_KEY=gsk_your_key_here` (Get one free at https://console.groq.com/keys).\n\n"
            f"{raw_results}"
        )

    try:
        from groq import Groq
        client = Groq(api_key=groq_api_key, max_retries=0)
        prompt = (
            f"You are a specialized technical research AI powered by Groq.\n"
            f"User Query: {query}\n\n"
            f"Real-Time Web Documentation & Sources:\n{raw_results}\n\n"
            f"Synthesize a clear, direct, and actionable technical explanation with code examples where applicable, "
            f"and list the source URLs at the end."
        )

        candidate_models = [
            "qwen/qwen3.8-27b",
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "llama-3.3-70b-versatile"
        ]
        
        ans = None
        used_model = None

        for model_id in candidate_models:
            try:
                completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "You are a senior developer intelligence assistant powered by Groq."},
                        {"role": "user", "content": prompt}
                    ],
                    model=model_id,
                    temperature=0.2,
                    max_tokens=800
                )
                content = completion.choices[0].message.content
                if content and len(content.strip()) > 10:
                    ans = content
                    used_model = model_id
                    break
            except Exception:
                continue

        if ans:
            return f"⚡ **Groq Intelligence ({used_model})**:\n\n{ans}\n\n🔗 **Live Search Results:**\n{raw_results}"
        else:
            return f"**Live Search Results:**\n\n{raw_results}"
    except Exception:
        return f"**Live Search Results:**\n\n{raw_results}"


@tool
def web_search(query: str, max_results: int = 4) -> str:
    """
    Search the public web and synthesize real-time documentation using Groq LLaMA-3.3.
    
    Args:
        query: The search term or question to query the web for.
        max_results: Number of search results to return (default: 4).
    
    Returns:
        Groq-synthesized summary of top search results with source citations.
    """
    import urllib.parse
    import xml.etree.ElementTree as ET
    import requests

    cleaned_query = query.strip()
    if not cleaned_query:
        return "Error: Empty search query provided."

    raw_out = ""

    # Strategy 1: High-speed sub-second direct web query (unblocked, 0.4s response)
    try:
        encoded = urllib.parse.quote_plus(cleaned_query)
        url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"
        resp = requests.get(url, timeout=3, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            items = root.findall(".//item")[:max_results]
            if items:
                formatted = [f"Search results for '{cleaned_query}':\n"]
                for i, item in enumerate(items, 1):
                    title = item.find("title").text if item.find("title") is not None else "Untitled"
                    link = item.find("link").text if item.find("link") is not None else ""
                    formatted.append(f"{i}. **{title}**\n   Source: {link}")
                raw_out = "\n\n".join(formatted)
    except Exception:
        pass

    # Strategy 2: DDGS fallback
    if not raw_out:
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(cleaned_query, max_results=max_results))
                if results:
                    formatted = [f"Search results for '{cleaned_query}':\n"]
                    for i, r in enumerate(results, 1):
                        title = r.get("title", "Untitled")
                        snippet = r.get("body", "No description")
                        href = r.get("href", "")
                        formatted.append(f"{i}. **{title}**\n   {snippet}\n   Source: {href}")
                    raw_out = "\n\n".join(formatted)
        except Exception:
            pass

    if not raw_out:
        raw_out = f"Technical search context query: '{cleaned_query}'."

    return _synthesize_with_groq(cleaned_query, raw_out)


