"""
Automated Verification & Unit Tests for WOLF DevSecOps Core Layers.
===================================================================
Verifies MCP config loading, GitHub & Groq search MCP tools,
persistent developer memory, and LangGraph context window trimming.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from memory.user_profile_store import UserProfileStore
from memory.context_manager import ContextManager
from mcp_service.config import load_mcp_server_configs
from langchain_core.messages import HumanMessage, AIMessage


class TestAgentComponents(unittest.TestCase):
    """Test suite verifying core agent infrastructure."""

    def test_mcp_config_loading(self):
        """Verify active engineering MCP server configurations load properly."""
        configs = load_mcp_server_configs()
        self.assertIn("github_service", configs)
        self.assertIn("web_search_service", configs)
        self.assertNotIn("system_diagnostics", configs)
        self.assertNotIn("advanced_math", configs)

    def test_github_mcp_server_tools(self):
        """Verify GitHub read-only MCP tools function properly."""
        from mcp_service.servers.github_server import list_repositories, list_issues
        repos = list_repositories(username="octocat", limit=2)
        self.assertIn("Repositories", repos)

        issues = list_issues(repo="octocat/Hello-World", limit=2)
        self.assertIn("issues", issues.lower())

    def test_web_search_mcp_server_tools(self):
        """Verify Groq-powered Web Search MCP tool responds cleanly."""
        from mcp_service.servers.search_server import search_web
        res = search_web(query="OWASP Top 10 Python security", max_results=2)
        self.assertIn("results", res.lower())

    def test_memory_profile_store(self):
        """Verify long-term engineering profile memory saves and retrieves."""
        test_store_path = "./data/test_profile.json"
        store = UserProfileStore(storage_path=test_store_path)
        store.set_fact("role", "DevSecOps Engineer")
        store.set_fact("standard", "OWASP Top 10")

        facts = store.get_all_facts()
        self.assertEqual(facts.get("role"), "DevSecOps Engineer")
        self.assertEqual(facts.get("standard"), "OWASP Top 10")

        if Path(test_store_path).exists():
            Path(test_store_path).unlink()

    def test_context_manager_trimming(self):
        """Verify context manager prunes when messages exceed limit."""
        cm = ContextManager(max_messages=4)
        messages = [
            HumanMessage(content="Msg 1"),
            AIMessage(content="Reply 1"),
            HumanMessage(content="Msg 2"),
            AIMessage(content="Reply 2"),
            HumanMessage(content="Msg 3"),
            AIMessage(content="Reply 3"),
        ]
        trimmed = cm.optimize_messages(messages)
        self.assertLessEqual(len(trimmed), 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
