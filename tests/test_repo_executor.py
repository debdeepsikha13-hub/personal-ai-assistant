"""
Unit Tests for On-Demand 2-Stage Repository Executor.
=====================================================
Verifies:
  1. Stage 1 automatically fixes bugs in submitted repositories.
  2. Stage 2 runs AFTER fixing and emits SECURE or INSECURE verdict clearly.
  3. GitHub URL parsing handles standard repository URLs cleanly.
"""

import tempfile
import unittest
from pathlib import Path
from core.repo_executor import OnDemandRepoExecutor, _parse_github_url


class TestOnDemandRepoExecutor(unittest.TestCase):
    """Tests on-demand repo execution (Stage 1 Bug Fix -> Stage 2 Security Verdict)."""

    def setUp(self):
        self.executor = OnDemandRepoExecutor()

    def test_01_parse_github_urls(self):
        """Standard GitHub repo URLs and owner/repo shorthand parse cleanly."""
        self.assertEqual(
            _parse_github_url("https://github.com/octocat/Hello-World"),
            ("octocat", "Hello-World", "https://github.com/octocat/Hello-World.git")
        )
        self.assertEqual(
            _parse_github_url("https://github.com/octocat/Hello-World.git"),
            ("octocat", "Hello-World", "https://github.com/octocat/Hello-World.git")
        )
        self.assertIsNone(_parse_github_url(r"C:\Users\DELL\project"))

    def test_02_buggy_and_insecure_repo_fixes_bugs_then_flags_insecure(self):
        """Must fix Stage 1 bugs, then emit INSECURE verdict when security flaws remain."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "friend_repo"
            repo.mkdir()
            app_py = repo / "main.py"
            app_py.write_text(
                "import os\n\n"
                "def calculate_average(numbers):\n"
                "    return round(sum(numbers) / len(numbers), 2)\n\n"
                "def check_val(x):\n"
                "    if x == None:\n"
                "        return 0\n"
                "    try:\n"
                "        return os.system(str(x))\n"
                "    except:\n"
                "        return -1\n",
                encoding="utf-8"
            )

            res = self.executor.execute(str(repo))
            self.assertEqual(res["status"], "completed")

            # Stage 1: Bugs detected & auto-fixed
            s1 = res["stage1_bugs"]
            self.assertGreaterEqual(s1["bugs_fixed_count"], 3)
            patched = app_py.read_text(encoding="utf-8")
            self.assertIn("if not numbers:", patched)
            self.assertIn("if x is None:", patched)
            self.assertIn("except Exception:", patched)

            # Stage 2: Security scan ran AFTER fixing and flagged os.system() as INSECURE
            s2 = res["stage2_security"]
            self.assertEqual(s2["verdict"], "INSECURE")
            self.assertGreaterEqual(s2["vulnerabilities_count"], 1)
            self.assertIn("INSECURE", s2["indicator"])

    def test_03_clean_repo_returns_secure_verdict(self):
        """A clean repo must pass Stage 1 and emit SECURE Grade A+."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "clean_repo"
            repo.mkdir()
            (repo / "utils.py").write_text(
                "def greet(name: str) -> str:\n"
                "    return f'Hello, {name}'\n",
                encoding="utf-8"
            )

            res = self.executor.execute(str(repo))
            self.assertEqual(res["status"], "completed")
            self.assertEqual(res["stage1_bugs"]["bugs_found_count"], 0)
            self.assertEqual(res["stage2_security"]["verdict"], "SECURE")
            self.assertEqual(res["stage2_security"]["overall_grade"], "A+")


if __name__ == "__main__":
    unittest.main()

