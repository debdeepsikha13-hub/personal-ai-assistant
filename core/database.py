"""
Central SQLite Relational Database & Audit Trail Store.
=======================================================
Provides real relational database persistence for WOLF:
  - Table: audit_reports (Tracks every repository bug remediation & security certification)
  - Uses native Python sqlite3 driver with ACID transactions and schema validation.
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from contextlib import contextmanager

from config.settings import get_settings
from utils.logger import setup_logger

logger = setup_logger("database")

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "security_reports.db"


class AuditDatabase:
    """Manages SQLite relational database storage and queries for WOLF audit logs."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _connect(self):
        """Thread-safe connection context manager with automatic commit and row factory."""
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Initialize relational SQL tables and indexes if not present."""
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS audit_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repo_label TEXT NOT NULL,
                    source_type TEXT NOT NULL DEFAULT 'github',
                    scanned_at TEXT NOT NULL,
                    duration_ms INTEGER NOT NULL DEFAULT 0,
                    bugs_found INTEGER NOT NULL DEFAULT 0,
                    bugs_fixed INTEGER NOT NULL DEFAULT 0,
                    remaining_bugs INTEGER NOT NULL DEFAULT 0,
                    agent_loop_iterations INTEGER NOT NULL DEFAULT 1,
                    security_grade TEXT NOT NULL DEFAULT 'N/A',
                    security_score INTEGER NOT NULL DEFAULT 0,
                    vulnerabilities_count INTEGER NOT NULL DEFAULT 0,
                    verdict TEXT NOT NULL DEFAULT 'INSECURE',
                    summary TEXT,
                    report_json TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_audit_scanned_at ON audit_reports(scanned_at DESC);
                CREATE INDEX IF NOT EXISTS idx_audit_repo_label ON audit_reports(repo_label);
                """
            )
        logger.info(f"SQLite Relational Database initialized at: {self.db_path}")

    def save_audit_report(self, execution_result: Dict[str, Any]) -> int:
        """
        Persist an on-demand repository execution result into SQLite.
        Returns the inserted record's primary key ID.
        """
        now = datetime.now(timezone.utc).isoformat()
        repo_meta = execution_result.get("repo", {})
        repo_label = repo_meta.get("repo_label", "unknown_target")
        source_type = repo_meta.get("source_type", "local")
        duration_ms = execution_result.get("duration_ms", 0)

        s1 = execution_result.get("stage1_bugs", {})
        s2 = execution_result.get("stage2_security", {})
        loop_info = s1.get("agent_loop", {})

        verdict = s2.get("verdict", "INSECURE")
        grade = s2.get("overall_grade", "N/A")
        score = s2.get("score", 0)
        vulns = s2.get("vulnerabilities_count", 0)

        bugs_found = s1.get("bugs_found_count", 0)
        bugs_fixed = s1.get("bugs_fixed_count", 0)
        remaining = s1.get("remaining_bugs_count", 0)
        loop_iter = loop_info.get("total_iterations", 1)

        summary = (
            f"Stage 1: {bugs_fixed}/{bugs_found} bugs fixed ({loop_iter} loop(s)) | "
            f"Stage 2: Grade {grade} ({score}/100) - {verdict}"
        )

        report_json = json.dumps(execution_result, ensure_ascii=False)

        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO audit_reports (
                    repo_label, source_type, scanned_at, duration_ms,
                    bugs_found, bugs_fixed, remaining_bugs, agent_loop_iterations,
                    security_grade, security_score, vulnerabilities_count,
                    verdict, summary, report_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    repo_label, source_type, now, duration_ms,
                    bugs_found, bugs_fixed, remaining, loop_iter,
                    grade, score, vulns, verdict, summary, report_json
                )
            )
            inserted_id = cur.lastrowid or 0

        logger.info(f"Saved audit report #{inserted_id} for '{repo_label}' into SQLite database.")
        return inserted_id

    def get_recent_reports(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Query the most recent repository audit reports from SQLite."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, repo_label, source_type, scanned_at, duration_ms,
                       bugs_found, bugs_fixed, remaining_bugs, agent_loop_iterations,
                       security_grade, security_score, vulnerabilities_count,
                       verdict, summary
                FROM audit_reports
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,)
            ).fetchall()

        return [dict(r) for r in rows]

    def get_report_by_id(self, report_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve full audit report JSON by primary key ID."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM audit_reports WHERE id = ?",
                (report_id,)
            ).fetchone()

        if not row:
            return None

        result = dict(row)
        try:
            result["report"] = json.loads(result["report_json"])
        except Exception:
            result["report"] = {}
        return result


_db_instance: Optional[AuditDatabase] = None

def get_audit_db() -> AuditDatabase:
    """Singleton getter for the SQLite audit database."""
    global _db_instance
    if _db_instance is None:
        _db_instance = AuditDatabase()
    return _db_instance

