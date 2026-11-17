"""
Web Search & Technical Intelligence Tool.
=========================================
Searches the web in real-time and synthesizes answers using Groq LLaMA-3.3.
"""

import os
from langchain_core.tools import tool
from duckduckgo_search import DDGS
from typing import Optional


def _synthesize_with_groq(query: str, raw_results: str) -> str:
    """Synthesizes web results using Groq LLaMA-3.3 if GROQ_API_KEY is available."""
    groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not groq_api_key:
        return (
            "⚠️ **Groq Search Synthesis Inactive: Missing GROQ_API_KEY**\n"
            "To enable Groq LLaMA-3.3 synthesis, paste your free Groq API key in `.env`:\n"
            "`GROQ_API_KEY=gsk_your_key_here` (Get one free at https://console.groq.com/keys).\n\n"
            f"{raw_results}"
        )

    try:
        from groq import Groq
        client = Groq(api_key=groq_api_key)
        prompt = (
            f"You are a specialized technical research AI powered by Groq LLaMA-3.3.\n"
            f"User Query: {query}\n\n"
            f"Real-Time Web Documentation & Sources:\n{raw_results}\n\n"
            f"Synthesize a clear, direct, and actionable technical explanation with code examples where applicable, "
            f"and list the source URLs at the end."
        )
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a senior developer intelligence assistant powered by Groq LLaMA-3.3."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.2,
            max_tokens=800
        )
        ans = completion.choices[0].message.content
        return f"⚡ **Groq LLaMA-3.3 Search Intelligence**:\n\n{ans}\n\n🔗 **Live Sources:**\n{raw_results}"
    except Exception as e:
        return f"⚠️ Groq Synthesis Error ({e}). Raw web search results:\n\n{raw_results}"


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
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            
            if not results:
                return f"No relevant web results found for query: '{query}'."

            formatted = [f"Search results for '{query}':\n"]
            for i, r in enumerate(results, 1):
                title = r.get("title", "Untitled")
                snippet = r.get("body", "No description")
                href = r.get("href", "")
                formatted.append(f"{i}. **{title}**\n   {snippet}\n   Source: {href}")

            raw_out = "\n\n".join(formatted)
            return _synthesize_with_groq(query, raw_out)

    except Exception as e:
        return f"Unable to perform web search at this moment: {str(e)}"


