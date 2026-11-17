"""
Unit Tests for Central Security Scanning Platform (OWASP / CWE SAST Engine).
============================================================================
Verifies detection of all 6 security rule categories (SEC-01 through SEC-06)
and validates clean certification on production code.
"""

import unittest
from core.security_scanner import SecurityVulnerabilityScanner
from core.bug_fixer_agent import TARGET_FILE_PATH
from tools.security_tool import run_security_audit


class TestSecurityVulnerabilityScanner(unittest.TestCase):
    """Validates SAST cybersecurity rule coverage and grading."""

    def setUp(self):
        self.scanner = SecurityVulnerabilityScanner()

    def test_01_clean_codebase_passes_grade_a_plus(self):
        """Production codebase/data_processor.py must score A+ with 0 vulnerabilities."""
        report = self.scanner.scan_file(TARGET_FILE_PATH)
        self.assertEqual(report["status"], "completed")
        self.assertTrue(report["is_secure"])
        self.assertEqual(report["vulnerabilities_count"], 0)
        self.assertEqual(report["overall_grade"], "A+")
        self.assertEqual(len(report["checklist"]), 6)

    def test_02_detect_code_and_command_injection_sec01(self):
        """SEC-01 must flag eval(), exec(), os.system(), and subprocess(shell=True)."""
        vuln_code = (
            "import os, subprocess\n"
            "def run_user(cmd):\n"
            "    eval(cmd)\n"
            "    os.system(cmd)\n"
            "    subprocess.run(cmd, shell=True)\n"
        )
        report = self.scanner.scan_code(vuln_code, filename="inj.py")
        self.assertFalse(report["is_secure"])
        rule_ids = [f["rule_id"] for f in report["findings"]]
        self.assertEqual(rule_ids.count("SEC-01"), 3)
        self.assertGreaterEqual(report["severity_counts"]["CRITICAL"], 3)

    def test_03_detect_hardcoded_secrets_sec02(self):
        """SEC-02 must flag hardcoded API tokens and plaintext passwords."""
        vuln_code = (
            "API_TOKEN = 'ghp_1234567890abcdef1234567890abcdef1234'\n"
            "db_password = 'SuperSecretProdPassword99!'\n"
        )
        report = self.scanner.scan_code(vuln_code, filename="secrets.py")
        rule_ids = [f["rule_id"] for f in report["findings"]]
        self.assertIn("SEC-02", rule_ids)
        self.assertGreaterEqual(report["vulnerabilities_count"], 2)

    def test_04_detect_sql_injection_sec03(self):
        """SEC-03 must flag dynamic unparameterized SQL queries in .execute()."""
        vuln_code = (
            "def get_user(cursor, username):\n"
            "    cursor.execute(f'SELECT * FROM users WHERE name = {username}')\n"
        )
        report = self.scanner.scan_code(vuln_code, filename="sqli.py")
        rule_ids = [f["rule_id"] for f in report["findings"]]
        self.assertIn("SEC-03", rule_ids)

    def test_05_detect_insecure_deserialization_sec04(self):
        """SEC-04 must flag pickle.loads() and yaml.load() without SafeLoader."""
        vuln_code = (
            "import pickle, yaml\n"
            "def decode(blob, text):\n"
            "    a = pickle.loads(blob)\n"
            "    b = yaml.load(text)\n"
            "    return a, b\n"
        )
        report = self.scanner.scan_code(vuln_code, filename="deser.py")
        rule_ids = [f["rule_id"] for f in report["findings"]]
        self.assertEqual(rule_ids.count("SEC-04"), 2)

    def test_06_detect_weak_crypto_and_tls_bypass_sec05(self):
        """SEC-05 must flag hashlib.md5() and requests.get(..., verify=False)."""
        vuln_code = (
            "import hashlib, requests\n"
            "h = hashlib.md5(b'pw').hexdigest()\n"
            "r = requests.get('https://internal.local', verify=False, timeout=5)\n"
        )
        report = self.scanner.scan_code(vuln_code, filename="crypto.py")
        rule_ids = [f["rule_id"] for f in report["findings"]]
        self.assertEqual(rule_ids.count("SEC-05"), 2)

    def test_07_detect_path_traversal_and_missing_timeout_sec06(self):
        """SEC-06 must flag path traversal in open(), tempfile.mktemp(), and unbounded requests."""
        vuln_code = (
            "import tempfile, requests\n"
            "f = open('../../etc/passwd')\n"
            "tmp = tempfile.mktemp()\n"
            "r = requests.get('https://example.com')\n"
        )
        report = self.scanner.scan_code(vuln_code, filename="resource.py")
        rule_ids = [f["rule_id"] for f in report["findings"]]
        self.assertEqual(rule_ids.count("SEC-06"), 3)

    def test_08_security_langchain_tool_executes(self):
        """Native LangChain run_security_audit tool must return formatted SAST report."""
        out = run_security_audit.invoke({})
        self.assertIn("Cybersecurity SAST Audit Report", out)
        self.assertIn("Grade A+", out)


if __name__ == "__main__":
    unittest.main()
