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

    def test_04_javascript_mern_repo_detection_and_fixing(self):
        """JavaScript/MERN repository must be detected, bugs patched, and security flaws audited."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "mern_repo"
            repo.mkdir()
            (repo / "pricing.js").write_text(
                "export function summarizeCart(items, coupon = '') {\n"
                "  const subtotal = 50;\n"
                "  let discount = 100;\n"
                "  if (coupon.toUpperCase() === 'FLAT100') discount = 100;\n"
                "  return { subtotal, discount, total: subtotal - discount };\n"
                "}\n",
                encoding="utf-8"
            )
            (repo / "server.js").write_text(
                "const express = require('express');\n"
                "const jwtSecret = 'hardcoded_production_token_999';\n"
                "eval(req.body.customCode);\n",
                encoding="utf-8"
            )

            res = self.executor.execute(str(repo))
            self.assertEqual(res["status"], "completed")

            # Check multi-language detection
            s1 = res["stage1_bugs"]
            self.assertEqual(s1["dominant_language"], "JavaScript / MERN Stack")
            self.assertEqual(s1["files_analyzed"], 2)
            self.assertGreaterEqual(s1["bugs_found_count"], 1)

            # Verify patch applied to pricing.js
            patched_pricing = (repo / "pricing.js").read_text(encoding="utf-8")
            self.assertIn("Math.max(0, subtotal - discount)", patched_pricing)

            # Check Stage 2 security audit flagged eval and jwtSecret
            s2 = res["stage2_security"]
            self.assertEqual(s2["verdict"], "INSECURE")
            self.assertGreaterEqual(s2["vulnerabilities_count"], 2)

    def test_05_decode_phase_inspects_without_modifying_files(self):
        """Phase 1 decode() must detect bugs, declare UNSECURE, and NOT modify files on disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "unpatched_repo"
            repo.mkdir()
            app_py = repo / "main.py"
            original_code = (
                "def calculate_average(numbers):\n"
                "    return round(sum(numbers) / len(numbers), 2)\n"
            )
            app_py.write_text(original_code, encoding="utf-8")

            # Run Phase 1: decode
            decode_res = self.executor.decode(str(repo))
            self.assertEqual(decode_res["status"], "completed")
            self.assertEqual(decode_res["phase"], "decoded")
            self.assertEqual(decode_res["verdict"], "UNSECURE / BUGS DETECTED")
            self.assertFalse(decode_res["is_secure"])
            self.assertTrue(decode_res["can_fix"])
            self.assertGreaterEqual(decode_res["stage1_bugs"]["bugs_found_count"], 1)

            # Code MUST remain unpatched in Phase 1
            current_code = app_py.read_text(encoding="utf-8")
            self.assertEqual(current_code, original_code)
            self.assertNotIn("if not numbers:", current_code)

            # Now run Phase 2: execute (Fix & Certify)
            exec_res = self.executor.execute(str(repo))
            self.assertEqual(exec_res["status"], "completed")
            self.assertEqual(exec_res["phase"], "certified")
            self.assertTrue(exec_res["is_secure"])
            self.assertIn("WOLF CERTIFIED SECURE", exec_res["verdict"])
            self.assertIn("if not numbers:", app_py.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

