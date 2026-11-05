"""
Web Search Tool.
================
Searches the web in real-time using DuckDuckGo (free, no API key required).

WHY THIS FOLDER MATTERS:
- If you want to switch to Tavily, Google Custom Search, Serper, or Bing,
  you modify ONLY this file.
"""

from langchain_core.tools import tool
from duckduckgo_search import DDGS
from typing import Optional


@tool
def web_search(query: str, max_results: int = 4) -> str:
    """
    Search the public web for real-time information, news, documentation, or facts.
    
    Args:
        query: The search term or question to query the web for.
        max_results: Number of search results to return (default: 4).
    
    Returns:
        Formatted summary of the top search results including titles and snippets.
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

            return "\n\n".join(formatted)

    except Exception as e:
        return f"Unable to perform web search at this moment: {str(e)}"

