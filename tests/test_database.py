"""
Unit Tests for SQLite Relational Database & Audit Trail.
========================================================
Verifies:
  1. Relational schema initializes correctly.
  2. ACID insert transactions persist execution audit reports.
  3. Querying recent reports and report by ID returns typed rows.
"""

import tempfile
import unittest
from pathlib import Path
from core.database import AuditDatabase


class TestAuditDatabase(unittest.TestCase):
    """Verifies SQLite persistence and queries."""

    def test_01_init_and_persist_audit_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_audit.db"
            db = AuditDatabase(db_path=db_path)

            mock_execution = {
                "status": "completed",
                "repo": {
                    "repo_label": "octocat/Hello-World",
                    "source_type": "github"
                },
                "duration_ms": 1420,
                "stage1_bugs": {
                    "bugs_found_count": 2,
                    "bugs_fixed_count": 2,
                    "remaining_bugs_count": 0,
                    "agent_loop": {"total_iterations": 1, "status": "RESOLVED"}
                },
                "stage2_security": {
                    "overall_grade": "A+",
                    "score": 100,
                    "vulnerabilities_count": 0,
                    "verdict": "SECURE"
                }
            }

            rec_id = db.save_audit_report(mock_execution)
            self.assertGreater(rec_id, 0)

            # Query recent
            recent = db.get_recent_reports(limit=5)
            self.assertEqual(len(recent), 1)
            row = recent[0]
            self.assertEqual(row["repo_label"], "octocat/Hello-World")
            self.assertEqual(row["verdict"], "SECURE")
            self.assertEqual(row["security_grade"], "A+")
            self.assertEqual(row["bugs_fixed"], 2)

            # Query by ID
            detail = db.get_report_by_id(rec_id)
            self.assertIsNotNone(detail)
            self.assertEqual(detail["repo_label"], "octocat/Hello-World")
            self.assertEqual(detail["report"]["duration_ms"], 1420)


if __name__ == "__main__":
    unittest.main()

