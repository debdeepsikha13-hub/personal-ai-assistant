"""
Unit Tests for Central Security Scanning Platform.
===================================================
Verifies the core architecture invariants:
  1. Missing Scan Visibility: Newly registered repos immediately surface as MISSING_SCAN.
  2. Zero-Touch Guarantee: Scanning a repository adds ZERO files to the target directory.
  3. Centralized Report Storage: Scan results persist in SQLite and update fleet coverage.
"""

import tempfile
import unittest
from pathlib import Path
from core.central_platform import CentralSecurityPlatform


class TestCentralSecurityPlatform(unittest.TestCase):
    """Validates Zero-Touch Central Security Scanning Platform invariants."""

    def test_01_missing_scan_visibility_and_zero_touch_scan(self):
        """A newly registered repo must be visibly MISSING_SCAN, then SCANNED with 0 files added."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test_reports.db")
            repo_dir = Path(tmpdir) / "sample_service"
            repo_dir.mkdir()
            src_file = repo_dir / "app.py"
            src_file.write_text("def add(a: int, b: int) -> int:\n    return a + b\n", encoding="utf-8")

            files_before = sorted(p.name for p in repo_dir.rglob("*"))

            platform = CentralSecurityPlatform(db_path=db_path, github_owner="test-org")
            reg = platform.register_local_repository("sample_service", str(repo_dir))
            self.assertEqual(reg["status"], "registered")

            # 1. Missing scan MUST be visible before scanning
            ov_before = platform.get_platform_overview()
            sample_before = next(r for r in ov_before["repositories"] if r["repo_name"] == "sample_service")
            self.assertEqual(sample_before["scan_status"], "MISSING_SCAN")
            self.assertGreaterEqual(ov_before["coverage"]["missing_scan_repos"], 1)

            # 2. Execute Zero-Touch Central Scan
            report = platform.scan_repository("sample_service")
            self.assertEqual(report["status"], "completed")
            self.assertEqual(report["overall_grade"], "A+")
            self.assertEqual(report["vulnerabilities_count"], 0)
            self.assertIsNotNone(report["report_id"])

            # 3. Verify ZERO-TOUCH INVARIANT: no files added to target repository!
            files_after = sorted(p.name for p in repo_dir.rglob("*"))
            self.assertEqual(files_before, files_after, "Zero-touch violated: files were modified/added to target repo!")

            # 4. Verify SQLite persistence and updated status
            ov_after = platform.get_platform_overview()
            sample_after = next(r for r in ov_after["repositories"] if r["repo_name"] == "sample_service")
            self.assertEqual(sample_after["scan_status"], "SCANNED")
            self.assertEqual(sample_after["overall_grade"], "A+")
            self.assertGreaterEqual(len(ov_after["recent_reports"]), 1)

    def test_02_vulnerable_repo_flagged_in_fleet(self):
        """A repository with vulnerabilities must be surfaced as VULNERABLE in central overview."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test_reports_vuln.db")
            repo_dir = Path(tmpdir) / "insecure_service"
            repo_dir.mkdir()
            (repo_dir / "handler.py").write_text(
                "import os\ndef run(cmd):\n    os.system(cmd)\n",
                encoding="utf-8"
            )

            platform = CentralSecurityPlatform(db_path=db_path, github_owner="test-org")
            platform.register_local_repository("insecure_service", str(repo_dir))
            report = platform.scan_repository("insecure_service")
            self.assertFalse(report["is_secure"])
            self.assertGreaterEqual(report["vulnerabilities_count"], 1)

            ov = platform.get_platform_overview()
            rec = next(r for r in ov["repositories"] if r["repo_name"] == "insecure_service")
            self.assertEqual(rec["scan_status"], "VULNERABLE")
            self.assertEqual(ov["coverage"]["vulnerable_repos"], 1)
            self.assertEqual(len(ov["current_state"]), 8)


if __name__ == "__main__":
    unittest.main()

