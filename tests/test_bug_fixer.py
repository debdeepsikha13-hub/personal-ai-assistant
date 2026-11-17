"""
Unit Tests for Autonomous DevSecOps Bug Fixer & Security Pipeline.
==================================================================
Verifies real-world bug detection, autonomous patching, QA verification,
and Stage 2 OWASP/CWE SAST cybersecurity scanning (with zero toy simulations).
"""

import tempfile
import unittest
from pathlib import Path
from core.bug_fixer_agent import GeneralCodeBugFixerAgent
from tools.bug_fixer_tool import run_bug_fixer_agent, run_code_quality_checklist


class TestGeneralCodeBugFixer(unittest.TestCase):
    """Verifies 2-stage autonomous DevSecOps pipeline."""

    def setUp(self):
        self.agent = GeneralCodeBugFixerAgent()

    def test_01_baseline_tests_pass(self):
        """Baseline workspace tests must pass 100% with zero security issues."""
        res = self.agent.run_tests()
        self.assertTrue(res["all_passed"], f"Baseline failed: {res.get('failures')}")
        self.assertEqual(res["total_tests"], 6)

    def test_02_no_toy_simulation_method(self):
        """Toy simulation helpers must not exist on production agent."""
        self.assertFalse(hasattr(self.agent, "inject_demo_bug"))

    def test_03_real_external_file_bug_detection_and_patch(self):
        """Agent must detect & autonomously patch real bugs in external Python files."""
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

    def test_04_full_pipeline_includes_stage2_security_audit(self):
        """Full pipeline must execute both Stage 1 QA and Stage 2 SAST Security Audit."""
        pipeline_res = self.agent.run_full_pipeline()
        v = pipeline_res["verification_results"]
        sec = pipeline_res["security_audit"]

        self.assertTrue(v["all_passed"])
        self.assertEqual(v["passed_count"], 6)
        self.assertEqual(v["failed_count"], 0)
        self.assertEqual(sec["overall_grade"], "A+")
        self.assertEqual(sec["vulnerabilities_count"], 0)

    def test_05_langchain_tools_callable(self):
        """Native LangChain tools must execute cleanly and include SAST audit."""
        report = run_code_quality_checklist.invoke({})
        self.assertIn("Code Quality Production Checklist", report)
        self.assertIn("6/6 Passed", report)

        full_report = run_bug_fixer_agent.invoke({"action": "full_pipeline"})
        self.assertIn("Cybersecurity SAST Audit", full_report)
        self.assertIn("Grade A+", full_report)


if __name__ == "__main__":
    unittest.main()
