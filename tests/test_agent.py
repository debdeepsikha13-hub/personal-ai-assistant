"""
Automated Verification & Unit Tests for the Personal AI Assistant.
==================================================================
Tests individual layers in isolation (Tools, Memory, Context Manager, StateGraph).
Run via: python tests/test_agent.py
"""

import sys
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.weather_tool import get_weather
from tools.calculator_tool import calculate
from tools.notes_tool import save_note, list_notes
from tools.memory_tool import remember_user_fact, get_user_facts
from memory.user_profile_store import UserProfileStore
from memory.context_manager import ContextManager
from mcp_service.config import load_mcp_server_configs
from langchain_core.messages import HumanMessage, AIMessage


class TestAgentComponents(unittest.TestCase):
    """Test suite verifying agent layers."""

    def test_mcp_config_loading(self):
        """Verify MCP server configurations load properly."""
        configs = load_mcp_server_configs()
        self.assertIn("system_diagnostics", configs)
        self.assertIn("advanced_math", configs)
        self.assertIn("github_service", configs)
        self.assertIn("web_search_service", configs)

    def test_github_mcp_server_tools(self):
        """Verify GitHub read-only tools function properly."""
        from mcp_service.servers.github_server import list_repositories, list_issues
        repos = list_repositories(username="octocat", limit=2)
        self.assertIn("Repositories", repos)

        issues = list_issues(repo="octocat/Hello-World", limit=2)
        self.assertIn("Issues", issues)

    def test_web_search_mcp_server_tools(self):
        """Verify Web Search MCP tools function properly."""
        from mcp_service.servers.search_server import search_web
        res = search_web(query="Python LangChain", max_results=2)
        self.assertIn("Search Results", res)

    def test_calculator_tool(self):
        """Verify calculator evaluates math correctly."""
        res1 = calculate.invoke({"expression": "25 * 4 + 10"})
        self.assertIn("110", res1)

        res2 = calculate.invoke({"expression": "sqrt(144)"})
        self.assertIn("12", res2)

    def test_weather_tool(self):
        """Verify weather tool responds with conditions."""
        res = get_weather.invoke({"location": "London"})
        self.assertIsInstance(res, str)
        self.assertIn("Weather", res)

    def test_notes_tool(self):
        """Verify saving and listing personal notes."""
        save_res = save_note.invoke({"title": "Test Title", "content": "Buy groceries"})
        self.assertIn("saved successfully", save_res)

        list_res = list_notes.invoke({})
        self.assertIn("Test Title", list_res)

    def test_memory_profile_store(self):
        """Verify long-term memory facts save and retrieve."""
        test_store_path = "./data/test_profile.json"
        store = UserProfileStore(storage_path=test_store_path)
        store.set_fact("preferred_name", "Developer")
        store.set_fact("favorite_editor", "VSCode")

        facts = store.get_all_facts()
        self.assertEqual(facts.get("preferred_name"), "Developer")
        self.assertEqual(facts.get("favorite_editor"), "VSCode")

        # Cleanup test file
        if Path(test_store_path).exists():
            Path(test_store_path).unlink()

    def test_context_manager_trimming(self):
        """Verify context manager prunes when messages exceed limit."""
        cm = ContextManager(max_messages=4)
        messages = [
            HumanMessage(content="Hello 1"),
            AIMessage(content="Hi 1"),
            HumanMessage(content="Hello 2"),
            AIMessage(content="Hi 2"),
            HumanMessage(content="Hello 3"),
            AIMessage(content="Hi 3"),
        ]
        trimmed = cm.optimize_messages(messages)
        self.assertLessEqual(len(trimmed), 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)

