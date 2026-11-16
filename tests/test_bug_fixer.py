"""
Unit Tests for Autonomous E-Commerce Bug Fixer Agent.
=====================================================
Verifies that:
1. E-Commerce cart passes baseline checklist.
2. Demo bug injection correctly triggers test failure.
3. Bug Fixer Agent autonomously detects, patches, and passes the QA checklist.
"""

import unittest
from core.bug_fixer_agent import ECommerceBugFixerAgent
from tools.bug_fixer_tool import run_bug_fixer_agent, run_ecommerce_test_checklist


class TestECommerceBugFixer(unittest.TestCase):
    """Verifies autonomous bug fixing pipeline."""

    def setUp(self):
        self.agent = ECommerceBugFixerAgent()

    def test_01_baseline_tests_pass(self):
        """Initial baseline tests must pass 100%."""
        res = self.agent.run_tests()
        self.assertTrue(res["all_passed"], f"Baseline failed: {res.get('failures')}")
        self.assertEqual(res["total_tests"], 6)

    def test_02_inject_bug_and_detect(self):
        """Injecting tax bug must be detected by scan_for_bugs()."""
        inject_res = self.agent.inject_demo_bug("tax_bug")
        self.assertIn(inject_res.get("status"), ["success", "info"])

        scan_res = self.agent.scan_for_bugs()
        self.assertTrue(scan_res["bug_found"], "Agent failed to detect injected bug!")
        self.assertEqual(scan_res["diagnosis"]["function"], "calculate_tax()")

    def test_03_autonomous_fix_and_certification(self):
        """Agent must autonomously apply patch and achieve 100% pass rate."""
        pipeline_res = self.agent.run_full_pipeline()
        v = pipeline_res["verification_results"]
        
        self.assertTrue(v["all_passed"], "Pipeline verification failed after patch!")
        self.assertEqual(v["passed_count"], 6)
        self.assertEqual(v["failed_count"], 0)

    def test_04_langchain_tools_callable(self):
        """Native LangChain tools must execute cleanly and return formatted string."""
        report = run_ecommerce_test_checklist.invoke({})
        self.assertIn("E-Commerce Production Checklist", report)
        self.assertIn("6/6 Passed", report)


if __name__ == "__main__":
    unittest.main()
