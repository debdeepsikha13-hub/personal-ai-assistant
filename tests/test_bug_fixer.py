"""
Unit Tests for Input-Driven DevSecOps Bug Fixer & Security Pipeline.
====================================================================
Verifies pure on-demand execution on user-provided Python files/repos
with zero dummy codebase defaults or toy simulations.
"""

import tempfile
import unittest
from pathlib import Path
from core.bug_fixer_agent import GeneralCodeBugFixerAgent
from tools.bug_fixer_tool import run_bug_fixer_agent, execute_repository_link


class TestGeneralCodeBugFixer(unittest.TestCase):
    """Verifies pure input-driven 2-stage DevSecOps pipeline."""

    def test_01_requires_explicit_target_path(self):
        """Agent must NOT default to any hardcoded dummy file when target_path is omitted."""
        agent = GeneralCodeBugFixerAgent()
        self.assertIsNone(agent.target_path)
        self.assertFalse(hasattr(agent, "inject_demo_bug"))
        res = agent.run_full_pipeline()
        self.assertEqual(res["pipeline_status"], "ERROR")

    def test_02_real_external_file_bug_detection_and_patch(self):
        """Agent must detect & autonomously patch real bugs in user-provided Python files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            buggy_file = Path(tmpdir) / "service.py"
            buggy_file.write_text(
                "import yaml\n\n"
                "def calculate_average(numbers):\n"
                "    return round(sum(numbers) / len(numbers), 2)\n\n"
                "def load_cfg(raw):\n"
                "    try:\n"
                "        return yaml.unsafe_load(raw)\n"
                "    except:\n"
                "        return {}\n",
                encoding="utf-8"
            )

            ext_agent = GeneralCodeBugFixerAgent(target_path=str(buggy_file))
            scan_res = ext_agent.scan_for_bugs()
            self.assertTrue(scan_res["bug_found"], "Failed to detect AST bug in external file!")

            pipeline_res = ext_agent.run_full_pipeline()
            self.assertEqual(pipeline_res["pipeline_status"], "COMPLETED")

            patched = buggy_file.read_text(encoding="utf-8")
            self.assertIn("if not numbers:", patched)
            self.assertIn("except Exception:", patched)
            self.assertIn("yaml.safe_load(", patched)
            self.assertTrue(pipeline_res["security_audit"]["is_secure"])

    def test_03_langchain_tools_require_input_and_execute_on_real_target(self):
        """Native LangChain tools must prompt when empty and execute cleanly on real target."""
        empty_msg = run_bug_fixer_agent.invoke({"action": "full_pipeline", "target_path": ""})
        self.assertIn("Please provide", empty_msg)

        with tempfile.TemporaryDirectory() as tmpdir:
            sample = Path(tmpdir) / "clean.py"
            sample.write_text("def add(a: int, b: int) -> int:\n    return a + b\n", encoding="utf-8")
            report = execute_repository_link.invoke({"repo_url_or_path": str(tmpdir)})
            self.assertIn("CODE IS SECURE", report)
            self.assertIn("Grade", report)


if __name__ == "__main__":
    unittest.main()
