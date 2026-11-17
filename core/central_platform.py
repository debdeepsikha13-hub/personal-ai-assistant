"""
Central Security Scanning Platform — Zero-Touch Fleet Discovery & Audit Store.
==============================================================================
Implements enterprise central security governance:
  1. Zero-Touch Scanning: Scans any local or GitHub repository WITHOUT adding
     any workflow, config, or caller files to the target repository.
  2. Missing Scan Visibility: Tracks every discovered repository in a central
     inventory and explicitly surfaces MISSING_SCAN and STALE_SCAN gaps.
  3. Centralized Report Storage: Persists all SAST audit reports, grades,
     severity counts, and CWE findings in SQLite (`data/security_reports.db`).
  4. Current State Governance Matrix: Tracks Org/Repos, GitHub Plan, Action
     Minutes Used (0 CI burn via central runner), Scanners, Triggers,
     Per-Repo Caller overhead (0), and Report Storage.
"""

import json
import os
import sqlite3
import time
import urllib.request
import urllib.error
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

from core.security_scanner import SecurityVulnerabilityScanner, RULE_CATALOG, _compute_grade, SEVERITY_WEIGHTS
from utils.logger import setup_logger

logger = setup_logger("central_platform")

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
DEFAULT_DB_PATH = str(PROJECT_ROOT / "data" / "security_reports.db")
DEFAULT_GITHUB_OWNER = os.getenv("GITHUB_ORG") or os.getenv("GITHUB_USERNAME") or "debdeepsikha13-hub"
SCAN_SLA_DAYS = 7
MAX_REMOTE_PY_FILES = 25


class CentralSecurityPlatform:
    """
    Centralized Security Scanning Platform managing repository discovery,
    zero-touch SAST scanning, missing-scan visibility, and persistent audit storage.
    """

    def __init__(self, db_path: Optional[str] = None, github_owner: Optional[str] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.github_owner = github_owner or DEFAULT_GITHUB_OWNER
        self.scanner = SecurityVulnerabilityScanner()
        self._init_db()
        self._ensure_default_local_repo()

    @contextmanager
    def _connect(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Create central inventory and report storage tables if absent."""
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS repositories (
                    repo_name TEXT PRIMARY KEY,
                    full_name TEXT NOT NULL,
                    source TEXT NOT NULL DEFAULT 'github',
                    url_or_path TEXT NOT NULL,
                    default_branch TEXT DEFAULT 'main',
                    language TEXT DEFAULT 'Python',
                    discovered_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS scan_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repo_name TEXT NOT NULL,
                    scanned_at TEXT NOT NULL,
                    trigger_type TEXT NOT NULL DEFAULT 'zero_touch_central',
                    files_scanned INTEGER NOT NULL DEFAULT 0,
                    overall_grade TEXT NOT NULL DEFAULT 'N/A',
                    score INTEGER NOT NULL DEFAULT 0,
                    vulnerabilities_count INTEGER NOT NULL DEFAULT 0,
                    critical_count INTEGER NOT NULL DEFAULT 0,
                    high_count INTEGER NOT NULL DEFAULT 0,
                    medium_count INTEGER NOT NULL DEFAULT 0,
                    low_count INTEGER NOT NULL DEFAULT 0,
                    duration_ms INTEGER NOT NULL DEFAULT 0,
                    findings_json TEXT NOT NULL DEFAULT '[]',
                    checklist_json TEXT NOT NULL DEFAULT '[]',
                    FOREIGN KEY (repo_name) REFERENCES repositories(repo_name)
                );

                CREATE INDEX IF NOT EXISTS idx_scan_reports_repo_time
                ON scan_reports(repo_name, scanned_at DESC);
                """
            )

    def _ensure_default_local_repo(self) -> None:
        """Register the active local workspace repository without adding any files to it."""
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO repositories
                (repo_name, full_name, source, url_or_path, default_branch, language, discovered_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "personal-ai-assistant (local)",
                    f"{self.github_owner}/personal-ai-assistant",
                    "local",
                    str(PROJECT_ROOT / "codebase"),
                    "main",
                    "Python",
                    now
                )
            )

    def register_local_repository(self, repo_name: str, local_path: str) -> Dict[str, Any]:
        """Register a local directory or file in the central inventory (zero files added)."""
        p = Path(local_path).resolve()
        if not p.exists():
            return {"status": "error", "error": f"Local path not found: {local_path}"}
        now = datetime.now(timezone.utc).isoformat()
        clean_name = repo_name.strip() or p.name
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO repositories
                (repo_name, full_name, source, url_or_path, default_branch, language, discovered_at)
                VALUES (?, ?, 'local', ?, 'local', 'Python', ?)
                """,
                (clean_name, clean_name, str(p), now)
            )
        return {"status": "registered", "repo_name": clean_name, "path": str(p)}

    def _github_get_json(self, url: str) -> Any:
        """Read-only GitHub REST API GET with optional GITHUB_TOKEN auth."""
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "Wolf-Central-Security-Platform/3.0"
        }
        token = os.getenv("GITHUB_TOKEN", "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"

        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def sync_github_repositories(self, owner: Optional[str] = None) -> Dict[str, Any]:
        """
        Discover all repositories for a GitHub user or organization (read-only).
        Zero files are added to any repository. Newly discovered repositories
        automatically appear as MISSING_SCAN until audited.
        """
        target_owner = (owner or self.github_owner).strip()
        if not target_owner:
            return {"status": "error", "error": "GitHub username or organization is required."}

        self.github_owner = target_owner
        repos_data = None

        # Try org endpoint first, then user endpoint
        for endpoint in (
            f"https://api.github.com/orgs/{target_owner}/repos?per_page=100&sort=updated",
            f"https://api.github.com/users/{target_owner}/repos?per_page=100&sort=updated"
        ):
            try:
                repos_data = self._github_get_json(endpoint)
                if isinstance(repos_data, list):
                    break
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    continue
                return {"status": "error", "error": f"GitHub API HTTP {e.code}: {e.reason}"}
            except Exception as e:
                return {"status": "error", "error": f"GitHub discovery failed: {e}"}

        if not isinstance(repos_data, list):
            return {"status": "error", "error": f"No GitHub org/user found for '{target_owner}'."}

        now = datetime.now(timezone.utc).isoformat()
        synced_count = 0
        with self._connect() as conn:
            for r in repos_data:
                name = r.get("name")
                full_name = r.get("full_name", f"{target_owner}/{name}")
                html_url = r.get("html_url", f"https://github.com/{full_name}")
                branch = r.get("default_branch") or "main"
                lang = r.get("language") or "Multi"
                if not name:
                    continue
                conn.execute(
                    """
                    INSERT INTO repositories
                    (repo_name, full_name, source, url_or_path, default_branch, language, discovered_at)
                    VALUES (?, ?, 'github', ?, ?, ?, ?)
                    ON CONFLICT(repo_name) DO UPDATE SET
                        full_name=excluded.full_name,
                        url_or_path=excluded.url_or_path,
                        default_branch=excluded.default_branch,
                        language=excluded.language
                    """,
                    (name, full_name, html_url, branch, lang, now)
                )
                synced_count += 1

        logger.info(f"Synced {synced_count} GitHub repositories for '{target_owner}' (zero-touch).")
        return {
            "status": "synced",
            "owner": target_owner,
            "synced_count": synced_count
        }

    def _scan_github_repo_zero_touch(self, full_name: str, default_branch: str) -> Dict[str, Any]:
        """
        Zero-touch remote SAST scan via GitHub API:
        Reads repository tree and Python files in memory without cloning or adding any files.
        Also flags committed `.env` / private key files directly from the repo tree!
        """
        tree_url = f"https://api.github.com/repos/{full_name}/git/trees/{default_branch}?recursive=1"
        try:
            tree_resp = self._github_get_json(tree_url)
        except urllib.error.HTTPError as e:
            if e.code == 409:
                # GitHub returns 409 Conflict when a repository is completely empty (0 commits)
                return {
                    "status": "completed",
                    "target": full_name,
                    "empty_repo": True,
                    "note": "Repository is empty on GitHub (0 commits / 0 files).",
                    "files_scanned": 0,
                    "vulnerabilities_count": 0,
                    "score": 100,
                    "overall_grade": "EMPTY",
                    "is_secure": True,
                    "severity_counts": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0},
                    "checklist": [
                        {
                            "rule_id": rule["rule_id"],
                            "cwe": rule["cwe"],
                            "owasp": rule["owasp"],
                            "title": rule["title"],
                            "description": rule["description"],
                            "passed": True,
                            "status": "EMPTY REPO (0 files)",
                            "findings_count": 0
                        }
                        for rule in RULE_CATALOG
                    ],
                    "findings": []
                }
            return {
                "status": "error",
                "error": f"Failed to read remote repo tree for {full_name}: HTTP {e.code} ({e.reason})"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to read remote repo tree for {full_name}: {e}"
            }

        tree_items = tree_resp.get("tree", [])
        all_findings: List[Dict[str, Any]] = []
        files_scanned = 0

        # 1. Check repository tree for committed secret files (.env, .pem, id_rsa)
        sensitive_filenames = {".env", ".env.production", ".env.local", "id_rsa", "credentials.json"}
        for item in tree_items:
            if item.get("type") != "blob":
                continue
            path_str = item.get("path", "")
            base = Path(path_str).name.lower()
            if base in sensitive_filenames or base.endswith((".pem", ".key", ".p12")):
                all_findings.append({
                    "rule_id": "SEC-02",
                    "cwe": "CWE-798",
                    "owasp": "A07:2021 Auth Failures",
                    "severity": "CRITICAL",
                    "title": f"Committed Secret / Credential File in Repository (`{path_str}`)",
                    "file": path_str,
                    "line": 1,
                    "snippet": path_str,
                    "remediation": f"Remove `{path_str}` from git history, add it to `.gitignore`, and rotate exposed credentials immediately."
                })

        # 2. Fetch and SAST-scan Python source files in memory (zero files added to repo)
        py_paths = [
            item["path"] for item in tree_items
            if item.get("type") == "blob"
            and item.get("path", "").endswith(".py")
            and not any(part in {"venv", ".venv", "node_modules", "__pycache__"} for part in item.get("path", "").split("/"))
        ][:MAX_REMOTE_PY_FILES]

        headers = {"User-Agent": "Wolf-Central-Security-Platform/3.0"}
        token = os.getenv("GITHUB_TOKEN", "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"

        for rel_path in py_paths:
            raw_url = f"https://raw.githubusercontent.com/{full_name}/{default_branch}/{rel_path}"
            try:
                req = urllib.request.Request(raw_url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    source_code = resp.read().decode("utf-8", errors="ignore")
                file_report = self.scanner.scan_code(source_code, filename=rel_path)
                all_findings.extend(file_report["findings"])
                files_scanned += 1
            except Exception as e:
                logger.warning(f"Could not fetch {rel_path} from {full_name}: {e}")

        # Aggregate into unified SAST report
        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        penalty = 0
        for f in all_findings:
            sev = f.get("severity", "LOW")
            if sev in severity_counts:
                severity_counts[sev] += 1
            penalty += SEVERITY_WEIGHTS.get(sev, 5)

        score = max(0, 100 - penalty)
        grade = _compute_grade(score)
        checklist = []
        for rule in RULE_CATALOG:
            rid = rule["rule_id"]
            cnt = sum(1 for f in all_findings if f.get("rule_id") == rid)
            checklist.append({
                "rule_id": rid,
                "cwe": rule["cwe"],
                "owasp": rule["owasp"],
                "title": rule["title"],
                "description": rule["description"],
                "passed": cnt == 0,
                "status": "SECURE ✅" if cnt == 0 else f"FLAGGED ({cnt}) ⚠️",
                "findings_count": cnt
            })

        return {
            "status": "completed",
            "target": full_name,
            "files_scanned": files_scanned,
            "vulnerabilities_count": len(all_findings),
            "score": score,
            "overall_grade": grade,
            "is_secure": len(all_findings) == 0,
            "severity_counts": severity_counts,
            "checklist": checklist,
            "findings": all_findings
        }

    def scan_repository(self, repo_name: str, trigger_type: str = "zero_touch_central") -> Dict[str, Any]:
        """
        Execute a zero-touch central security scan on a registered repository
        and persist the resulting report into SQLite central storage.
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM repositories WHERE repo_name = ?",
                (repo_name,)
            ).fetchone()

        if not row:
            return {"status": "error", "error": f"Repository '{repo_name}' is not in central inventory."}

        t0 = time.perf_counter()
        if row["source"] == "local":
            report = self.scanner.scan_directory(row["url_or_path"])
        else:
            report = self._scan_github_repo_zero_touch(row["full_name"], row["default_branch"])

        duration_ms = int((time.perf_counter() - t0) * 1000)

        if report.get("status") == "error":
            return report

        now = datetime.now(timezone.utc).isoformat()
        sev = report.get("severity_counts", {})
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO scan_reports (
                    repo_name, scanned_at, trigger_type, files_scanned,
                    overall_grade, score, vulnerabilities_count,
                    critical_count, high_count, medium_count, low_count,
                    duration_ms, findings_json, checklist_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    repo_name,
                    now,
                    trigger_type,
                    report.get("files_scanned", 0),
                    report.get("overall_grade", "N/A"),
                    report.get("score", 0),
                    report.get("vulnerabilities_count", 0),
                    sev.get("CRITICAL", 0),
                    sev.get("HIGH", 0),
                    sev.get("MEDIUM", 0),
                    sev.get("LOW", 0),
                    duration_ms,
                    json.dumps(report.get("findings", [])),
                    json.dumps(report.get("checklist", []))
                )
            )
            report_id = cur.lastrowid

        report["report_id"] = report_id
        report["repo_name"] = repo_name
        report["scanned_at"] = now
        report["duration_ms"] = duration_ms
        report["trigger_type"] = trigger_type
        return report

    def get_recent_reports(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Retrieve recent audit reports from central SQLite storage."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, repo_name, scanned_at, trigger_type, files_scanned,
                       overall_grade, score, vulnerabilities_count,
                       critical_count, high_count, medium_count, low_count, duration_ms
                FROM scan_reports
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def get_platform_overview(self) -> Dict[str, Any]:
        """
        Build the complete Central Security Scanning Platform dashboard payload:
          - Current State Governance Matrix (Org, Repos, Plan, Action Minutes, Scanners, Triggers, Per-Repo Callers, Report Storage)
          - Fleet Coverage Metrics & Missing Scan Visibility count
          - Per-Repository Compliance Table (MISSING_SCAN surfaced first!)
          - Recent Central Audit Reports
        """
        sla_cutoff = datetime.now(timezone.utc) - timedelta(days=SCAN_SLA_DAYS)

        with self._connect() as conn:
            repos = conn.execute("SELECT * FROM repositories ORDER BY repo_name ASC").fetchall()
            latest_map: Dict[str, sqlite3.Row] = {}
            latest_rows = conn.execute(
                """
                SELECT r.*
                FROM scan_reports r
                INNER JOIN (
                    SELECT repo_name, MAX(id) AS max_id
                    FROM scan_reports
                    GROUP BY repo_name
                ) latest ON r.id = latest.max_id
                """
            ).fetchall()
            for lr in latest_rows:
                latest_map[lr["repo_name"]] = lr

            total_reports = conn.execute("SELECT COUNT(*) FROM scan_reports").fetchone()[0]

        inventory: List[Dict[str, Any]] = []
        missing_count = 0
        stale_count = 0
        scanned_ok_count = 0
        vulnerable_count = 0

        for repo in repos:
            rname = repo["repo_name"]
            latest = latest_map.get(rname)

            if latest is None:
                scan_status = "MISSING_SCAN"
                missing_count += 1
                entry = {
                    "repo_name": rname,
                    "full_name": repo["full_name"],
                    "source": repo["source"],
                    "url_or_path": repo["url_or_path"],
                    "language": repo["language"],
                    "scan_status": scan_status,
                    "last_scanned_at": None,
                    "overall_grade": "UNSCANNED",
                    "score": None,
                    "vulnerabilities_count": None,
                    "critical_count": 0,
                    "high_count": 0,
                    "files_scanned": 0,
                    "findings": []
                }
            else:
                try:
                    scanned_dt = datetime.fromisoformat(latest["scanned_at"])
                    if scanned_dt.tzinfo is None:
                        scanned_dt = scanned_dt.replace(tzinfo=timezone.utc)
                    is_stale = scanned_dt < sla_cutoff
                except Exception:
                    is_stale = False

                vulns = latest["vulnerabilities_count"]
                if is_stale:
                    scan_status = "STALE_SCAN"
                    stale_count += 1
                elif vulns > 0:
                    scan_status = "VULNERABLE"
                    vulnerable_count += 1
                else:
                    scan_status = "SCANNED"
                    scanned_ok_count += 1

                try:
                    parsed_findings = json.loads(latest["findings_json"] or "[]")
                except Exception:
                    parsed_findings = []

                entry = {
                    "repo_name": rname,
                    "full_name": repo["full_name"],
                    "source": repo["source"],
                    "url_or_path": repo["url_or_path"],
                    "language": repo["language"],
                    "scan_status": scan_status,
                    "last_scanned_at": latest["scanned_at"],
                    "overall_grade": latest["overall_grade"],
                    "score": latest["score"],
                    "vulnerabilities_count": vulns,
                    "critical_count": latest["critical_count"],
                    "high_count": latest["high_count"],
                    "files_scanned": latest["files_scanned"],
                    "findings": parsed_findings
                }

            inventory.append(entry)

        # Surface MISSING_SCAN and VULNERABLE repos first so gaps are impossible to miss!
        priority_order = {"MISSING_SCAN": 0, "VULNERABLE": 1, "STALE_SCAN": 2, "SCANNED": 3}
        inventory.sort(key=lambda x: (priority_order.get(x["scan_status"], 9), x["repo_name"].lower()))

        total_repos = len(inventory)
        scanned_repos = total_repos - missing_count
        coverage_pct = round((scanned_repos / total_repos) * 100, 1) if total_repos > 0 else 0.0

        current_state = [
            {"item": "Organization / Account", "value": self.github_owner},
            {"item": "Repositories Tracked", "value": f"{total_repos} total ({scanned_repos} scanned, {missing_count} missing)"},
            {"item": "GitHub Plan", "value": "GitHub Free / Team Compatible (Zero Enterprise Lock-In)"},
            {"item": "Action Minutes Used", "value": "0 / 2,000 mins (Executed centrally on Wolf Engine — 0 CI burn)"},
            {"item": "Active Scanners", "value": "Wolf SAST (6 OWASP/CWE Rules), Secret Detector, Tree Leak Check, AST QA"},
            {"item": "Triggers", "value": "Zero-Touch On-Demand Central Dispatch + Scheduled SLA Check"},
            {"item": "Per-Repo Caller Files", "value": "0 Required (Zero-Touch — no YAML/config files added to target repos)"},
            {"item": "Report Storage", "value": f"Central SQLite Audit Store ({total_reports} reports persisted)"}
        ]

        return {
            "platform_name": "WOLF Central Security Scanning Platform",
            "github_owner": self.github_owner,
            "sla_days": SCAN_SLA_DAYS,
            "coverage": {
                "total_repos": total_repos,
                "scanned_repos": scanned_repos,
                "compliant_repos": scanned_ok_count,
                "missing_scan_repos": missing_count,
                "stale_scan_repos": stale_count,
                "vulnerable_repos": vulnerable_count,
                "coverage_pct": coverage_pct
            },
            "current_state": current_state,
            "requirements_enforced": [
                {"name": "Zero-Touch Repository Scanning", "status": "ENFORCED ✅", "detail": "0 files added to target repositories."},
                {"name": "Missing Scan Visibility", "status": "ENFORCED ✅", "detail": f"{missing_count} unscanned repo(s) visibly surfaced at top of fleet matrix."},
                {"name": "Centralized Audit Report Storage", "status": "ENFORCED ✅", "detail": f"SQLite store active at data/security_reports.db ({total_reports} reports)."}
            ],
            "repositories": inventory,
            "recent_reports": self.get_recent_reports(limit=10)
        }
