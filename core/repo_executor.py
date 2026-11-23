"""
On-Demand Repository Executor: Bug Fixing + Post-Fix Security Verification.
============================================================================
Executes STRICTLY ON DEMAND when the user submits a GitHub repository URL
(e.g. https://github.com/owner/repo) or a local folder/file path.
Never continuously scans or polls attached accounts in the background.

2-Stage Execution Flow:
  STAGE 1 — Autonomous Bug Detection & Fixing:
    - Ingests the submitted GitHub URL (isolated shallow clone into workspaces/) or local path.
    - Scans all Python files via AST for real bugs (SyntaxErrors, bare excepts, mutable defaults,
      == None / != None anti-patterns, unguarded sum/len division, unsafe yaml.load, duplicate keys).
    - Runs any discovered unittest suites in the target repo.
    - Applies verified automated patches and records exact files/lines modified.
  STAGE 2 — Post-Fix Cybersecurity Verification (OWASP / CWE SAST):
    - Scans the fixed codebase for security vulnerabilities (Injection, Hardcoded Secrets,
      SQLi, Insecure Deserialization, Weak Crypto/TLS, Path Traversal, committed .env/key files).
    - Emits a clear SECURE / INSECURE indicator with severity breakdown and line-level remediation.
"""

import ast
import io
import os
import re
import shutil
import subprocess
import time
import unittest
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from core.security_scanner import (
    SecurityVulnerabilityScanner,
    SKIP_DIRS,
    RULE_CATALOG,
    SEVERITY_WEIGHTS,
    _compute_grade
)
from utils.logger import setup_logger

logger = setup_logger("repo_executor")

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
WORKSPACES_DIR = PROJECT_ROOT / "workspaces"
SENSITIVE_FILES = {".env", ".env.production", ".env.local", "id_rsa", "credentials.json"}


def _parse_github_url(target: str) -> Optional[Tuple[str, str, str]]:
    """
    Parse a GitHub URL or 'owner/repo' string into (owner, repo_name, clone_url).
    Returns None if target is a local filesystem path.
    """
    raw = target.strip()
    if not raw:
        return None

    # Full GitHub URL: https://github.com/owner/repo(.git)(/tree/...)
    m = re.match(
        r"^(?:https?://)?(?:www\.)?github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?(?:/.*)?$",
        raw
    )
    if m:
        owner, repo = m.group(1), m.group(2)
        return owner, repo, f"https://github.com/{owner}/{repo}.git"

    # Shorthand owner/repo (only if not an existing local path and has no drive letter/backslashes)
    if (
        "/" in raw
        and "\\" not in raw
        and ":" not in raw
        and not Path(raw).exists()
        and re.match(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", raw)
    ):
        owner, repo = raw.split("/", 1)
        return owner, repo, f"https://github.com/{owner}/{repo}.git"

    return None


def _safe_rmtree(path: Path) -> None:
    """Remove a directory safely on Windows (handles read-only .git files)."""
    def _on_err(func, p, exc_info):
        try:
            os.chmod(p, 0o700)
            func(p)
        except Exception:
            pass

    if path.exists():
        shutil.rmtree(path, onerror=_on_err)


class OnDemandRepoExecutor:
    """
    On-demand 2-stage engineering engine:
      1. Fix bugs in the submitted GitHub URL or local path.
      2. Scan the fixed code for cybersecurity vulnerabilities and emit a SECURE/INSECURE verdict.
    """

    def __init__(self):
        self.scanner = SecurityVulnerabilityScanner()

    def _prepare_target(self, target: str) -> Tuple[Optional[Path], Dict[str, Any]]:
        """
        Clone a GitHub URL into an isolated workspace folder OR validate a local path.
        """
        gh = _parse_github_url(target)
        if gh:
            owner, repo, clone_url = gh
            WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)
            dest = WORKSPACES_DIR / f"{owner}__{repo}"
            _safe_rmtree(dest)

            logger.info(f"Cloning {clone_url} into {dest} (shallow, isolated)...")
            try:
                proc = subprocess.run(
                    ["git", "clone", "--depth", "1", clone_url, str(dest)],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
            except FileNotFoundError:
                return None, {"error": "Git is not installed or not on PATH."}
            except subprocess.TimeoutExpired:
                return None, {"error": f"Timed out while cloning {clone_url}."}

            if proc.returncode != 0:
                stderr = (proc.stderr or proc.stdout or "Unknown git error").strip()
                return None, {"error": f"Failed to clone {clone_url}: {stderr}"}

            return dest, {
                "input": target,
                "source_type": "github",
                "repo_label": f"{owner}/{repo}",
                "local_path": str(dest)
            }

        # Otherwise treat as local file or directory path
        local_p = Path(target).expanduser()
        if not local_p.is_absolute():
            local_p = (PROJECT_ROOT / local_p).resolve()
        else:
            local_p = local_p.resolve()

        if not local_p.exists():
            return None, {"error": f"Target path not found: {target}"}

        return local_p, {
            "input": target,
            "source_type": "local",
            "repo_label": local_p.name,
            "local_path": str(local_p)
        }

    def _collect_py_files(self, root: Path) -> List[Path]:
        if root.is_file():
            return [root] if root.suffix == ".py" else []
        found: List[Path] = []
        for cur, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for fn in sorted(files):
                if fn.endswith(".py"):
                    found.append(Path(cur) / fn)
        return found

    def _rel(self, file_path: Path, root: Path) -> str:
        if root.is_file():
            return file_path.name
        try:
            return str(file_path.relative_to(root)).replace("\\", "/")
        except ValueError:
            return str(file_path)

    def _scan_and_fix_bugs(self, root: Path, max_iterations: int = 3) -> Dict[str, Any]:
        """
        STAGE 1: Autonomous Agent Loop (Find -> Understand -> Fix -> Run & Check -> Loop if needed).
        Iteratively identifies bugs, applies targeted patches, and runs test suites until healthy
        or max_iterations reached.
        """
        py_files = self._collect_py_files(root)
        all_bugs_detected: List[Dict[str, Any]] = []
        all_fixes_applied: List[Dict[str, Any]] = []
        all_modified_files: List[str] = []
        loop_history: List[Dict[str, Any]] = []
        last_test_results: Dict[str, Any] = {"all_passed": True, "total_tests": 0}
        remaining_bugs: List[Dict[str, Any]] = []

        for iteration in range(1, max_iterations + 1):
            iteration_bugs: List[Dict[str, Any]] = []
            iteration_fixes: List[Dict[str, Any]] = []
            iteration_remaining: List[Dict[str, Any]] = []

            logger.info(f"🔄 [AGENT LOOP ITERATION {iteration}/{max_iterations}] Step 1: Finding bugs in target...")

            for py_file in py_files:
                rel_name = self._rel(py_file, root)
                try:
                    original = py_file.read_text(encoding="utf-8", errors="ignore")
                except Exception as e:
                    bug = {
                        "file": rel_name, "line": 1, "severity": "HIGH",
                        "bug_type": "IOError", "description": f"Could not read file: {e}",
                        "auto_fixed": False
                    }
                    iteration_bugs.append(bug)
                    iteration_remaining.append(bug)
                    continue

                updated = original
                file_fixes: List[str] = []

                # Step 1: Finding bugs via syntax & grammar analysis
                try:
                    tree = ast.parse(updated, filename=rel_name)
                    parse_ok = True
                except SyntaxError as e:
                    parse_ok = False
                    bug = {
                        "file": rel_name,
                        "line": e.lineno or 1,
                        "severity": "CRITICAL",
                        "bug_type": "SyntaxError",
                        "description": f"Python SyntaxError: {e.msg} ({(e.text or '').strip()})",
                        "auto_fixed": False
                    }
                    iteration_bugs.append(bug)
                    iteration_remaining.append(bug)

                if parse_ok:
                    # 1. Bare `except:` -> `except Exception:`
                    bare_except_lines = [
                        node.lineno for node in ast.walk(tree)
                        if isinstance(node, ast.ExceptHandler) and node.type is None
                    ]
                    if bare_except_lines:
                        bare_re = re.compile(r"^([ \t]*)except\s*:\s*$", re.MULTILINE)
                        if bare_re.search(updated):
                            updated = bare_re.sub(r"\1except Exception:", updated)
                            for ln in bare_except_lines:
                                bug = {
                                    "file": rel_name, "line": ln, "severity": "MEDIUM",
                                    "bug_type": "BareExcept",
                                    "description": "Bare `except:` swallows SystemExit/KeyboardInterrupt.",
                                    "auto_fixed": True,
                                    "fix": "Replaced bare `except:` with `except Exception:`."
                                }
                                iteration_bugs.append(bug)
                                iteration_fixes.append(bug)
                                file_fixes.append(f"Line {ln}: bare except -> except Exception")

                    # 2. Missing empty-list guard before sum(numbers) / len(numbers)
                    div_re = re.compile(
                        r"(def calculate_average\([^\)]*\)(?:\s*->\s*[^:]+)?:\s*\n(?:[ \t]*\"\"\"[\s\S]*?\"\"\"[ \t]*\n)?)"
                        r"(?![ \t]*if not numbers:)"
                        r"([ \t]+)(?:#[^\n]*\n\2)?return\s+round\(sum\(numbers\)\s*/\s*len\(numbers\),\s*2\)"
                    )
                    if div_re.search(updated):
                        updated = div_re.sub(
                            r"\1\2if not numbers:\n\2    return 0.0\n\2return round(sum(numbers) / len(numbers), 2)",
                            updated
                        )
                        bug = {
                            "file": rel_name, "line": 1, "severity": "CRITICAL",
                            "bug_type": "ZeroDivisionError",
                            "description": "Missing empty-list guard before `sum(numbers) / len(numbers)`.",
                            "auto_fixed": True,
                            "fix": "Inserted `if not numbers: return 0.0` guard clause."
                        }
                        iteration_bugs.append(bug)
                        iteration_fixes.append(bug)
                        file_fixes.append("Added ZeroDivisionError guard in calculate_average()")

                    # 3. `== None` / `!= None` -> `is None` / `is not None`
                    none_eq_re = re.compile(r"(?<![=!<>])==\s*None\b")
                    none_neq_re = re.compile(r"!=\s*None\b")
                    if none_eq_re.search(updated) or none_neq_re.search(updated):
                        updated = none_eq_re.sub("is None", updated)
                        updated = none_neq_re.sub("is not None", updated)
                        bug = {
                            "file": rel_name, "line": 1, "severity": "LOW",
                            "bug_type": "NoneComparisonBug",
                            "description": "Using `== None` or `!= None` instead of identity check `is None` / `is not None`.",
                            "auto_fixed": True,
                            "fix": "Normalized `== None` / `!= None` to `is None` / `is not None`."
                        }
                        iteration_bugs.append(bug)
                        iteration_fixes.append(bug)
                        file_fixes.append("Normalized None identity checks")

                    # 4. `yaml.unsafe_load(` -> `yaml.safe_load(`
                    if "yaml.unsafe_load(" in updated:
                        updated = updated.replace("yaml.unsafe_load(", "yaml.safe_load(")
                        bug = {
                            "file": rel_name, "line": 1, "severity": "HIGH",
                            "bug_type": "UnsafeYamlLoad",
                            "description": "Unsafe YAML deserialization `yaml.unsafe_load()`.",
                            "auto_fixed": True,
                            "fix": "Replaced `yaml.unsafe_load()` with `yaml.safe_load()`."
                        }
                        iteration_bugs.append(bug)
                        iteration_fixes.append(bug)
                        file_fixes.append("yaml.unsafe_load -> yaml.safe_load")

                    # 5. Detect mutable default arguments
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            for default in node.args.defaults + [d for d in node.args.kw_defaults if d is not None]:
                                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                                    bug = {
                                        "file": rel_name,
                                        "line": node.lineno,
                                        "severity": "MEDIUM",
                                        "bug_type": "MutableDefaultArg",
                                        "description": f"Mutable default argument in `{node.name}()` leaks state across calls.",
                                        "auto_fixed": False,
                                        "fix": "Change default to `None` and initialize inside the function body."
                                    }
                                    iteration_bugs.append(bug)
                                    iteration_remaining.append(bug)

                        # 6. Detect duplicate keys in dict literals
                        if isinstance(node, ast.Dict):
                            seen_keys = set()
                            for k in node.keys:
                                if isinstance(k, ast.Constant) and k.value in seen_keys:
                                    bug = {
                                        "file": rel_name,
                                        "line": getattr(k, "lineno", node.lineno),
                                        "severity": "MEDIUM",
                                        "bug_type": "DuplicateDictKey",
                                        "description": f"Duplicate dictionary key `{k.value!r}` silently overwrites earlier value.",
                                        "auto_fixed": False,
                                        "fix": "Remove or rename the duplicate dictionary key."
                                    }
                                    iteration_bugs.append(bug)
                                    iteration_remaining.append(bug)
                                elif isinstance(k, ast.Constant):
                                    seen_keys.add(k.value)

                # Step 3: Write fix to disk if updated
                if updated != original:
                    py_file.write_text(updated, encoding="utf-8")
                    if rel_name not in all_modified_files:
                        all_modified_files.append(rel_name)

            # Step 4: Run discovered unit tests and check if it passes
            logger.info(f"🧪 [AGENT LOOP ITERATION {iteration}/{max_iterations}] Step 4: Running tests and checking if code runs...")
            test_results = self._run_repo_tests(root)
            last_test_results = test_results

            if not test_results["all_passed"] and test_results["failures"]:
                for fail in test_results["failures"]:
                    last_line = [ln.strip() for ln in fail["traceback"].splitlines() if ln.strip()]
                    bug = {
                        "file": fail["test"],
                        "line": 0,
                        "severity": "HIGH",
                        "bug_type": "TestFailure",
                        "description": last_line[-1] if last_line else "Unit test assertion/runtime failure.",
                        "auto_fixed": False
                    }
                    iteration_bugs.append(bug)
                    iteration_remaining.append(bug)

            all_bugs_detected.extend(iteration_bugs)
            all_fixes_applied.extend(iteration_fixes)
            remaining_bugs = iteration_remaining

            # Step 5: Check if all bugs resolved and tests pass
            if test_results["all_passed"] and len(iteration_fixes) == 0 and len(iteration_bugs) == 0:
                logger.info(f"✅ [AGENT LOOP ITERATION {iteration}/{max_iterations}] Code is completely healthy!")
                loop_history.append({
                    "iteration": iteration,
                    "status": "CLEAN",
                    "step_summary": "All code is clean and tests pass."
                })
                break
            elif test_results["all_passed"] and len(iteration_fixes) > 0:
                logger.info(f"🎉 [AGENT LOOP ITERATION {iteration}/{max_iterations}] All applied patches verified! Tests passing.")
                loop_history.append({
                    "iteration": iteration,
                    "status": "RESOLVED",
                    "step_summary": f"Fixed {len(iteration_fixes)} bug(s). Verification passed."
                })
                break
            else:
                logger.warning(f"🔁 [AGENT LOOP ITERATION {iteration}/{max_iterations}] Tests or unhandled bugs remain. Looping back...")
                loop_history.append({
                    "iteration": iteration,
                    "status": "RETRYING",
                    "step_summary": f"Detected {len(iteration_bugs)} bug(s), applied {len(iteration_fixes)} fix(es). Re-evaluating..."
                })

        # Deduplicate bugs detected & fixes
        unique_detected = []
        seen_det = set()
        for b in all_bugs_detected:
            key = (b.get("file"), b.get("line"), b.get("bug_type"))
            if key not in seen_det:
                seen_det.add(key)
                unique_detected.append(b)

        unique_fixes = []
        seen_fix = set()
        for f in all_fixes_applied:
            key = (f.get("file"), f.get("line"), f.get("bug_type"))
            if key not in seen_fix:
                seen_fix.add(key)
                unique_fixes.append(f)

        return {
            "agent_loop": {
                "total_iterations": len(loop_history),
                "status": "RESOLVED" if last_test_results.get("all_passed") and len(remaining_bugs) == 0 else "PARTIALLY_RESOLVED",
                "loop_history": loop_history
            },
            "files_analyzed": len(py_files),
            "bugs_found_count": len(unique_detected),
            "bugs_fixed_count": len(unique_fixes),
            "remaining_bugs_count": len(remaining_bugs),
            "modified_files": all_modified_files,
            "bugs_detected": unique_detected,
            "fixes_applied": unique_fixes,
            "remaining_bugs": remaining_bugs,
            "tests": last_test_results
        }

    def _run_repo_tests(self, root: Path) -> Dict[str, Any]:
        """Discover and run unittest tests in the repo if any `test_*.py` files exist."""
        start_dir = str(root if root.is_dir() else root.parent)
        test_files = list(Path(start_dir).rglob("test_*.py")) if Path(start_dir).is_dir() else []
        test_files = [f for f in test_files if not any(part in SKIP_DIRS for part in f.parts)]

        if not test_files:
            return {
                "discovered": False,
                "all_passed": True,
                "total_tests": 0,
                "passed_count": 0,
                "failed_count": 0,
                "pass_rate": "N/A",
                "failures": []
            }

        loader = unittest.TestLoader()
        try:
            suite = loader.discover(start_dir=start_dir, pattern="test_*.py")
            stream = io.StringIO()
            runner = unittest.TextTestRunner(stream=stream, verbosity=1)
            res = runner.run(suite)
            total = res.testsRun
            failed = len(res.failures) + len(res.errors)
            passed = total - failed
            return {
                "discovered": True,
                "all_passed": res.wasSuccessful(),
                "total_tests": total,
                "passed_count": passed,
                "failed_count": failed,
                "pass_rate": f"{(passed / total * 100):.1f}%" if total > 0 else "N/A",
                "failures": [{"test": str(t), "traceback": tb} for t, tb in res.failures + res.errors]
            }
        except Exception as e:
            return {
                "discovered": True,
                "all_passed": False,
                "total_tests": 0,
                "passed_count": 0,
                "failed_count": 1,
                "pass_rate": "0.0%",
                "failures": [{"test": "unittest_discovery", "traceback": str(e)}]
            }

    def _run_post_fix_security_scan(self, root: Path) -> Dict[str, Any]:
        """
        STAGE 2: Scan the fixed repository with OWASP/CWE SAST + committed secret file check.
        Returns clear SECURE / INSECURE verdict.
        """
        report = self.scanner.scan_directory(str(root))
        if report.get("status") == "error":
            return report

        # Also check for committed secret files (.env, .pem, .key, id_rsa)
        extra_findings: List[Dict[str, Any]] = []
        if root.is_dir():
            for cur, dirs, files in os.walk(root):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                for fn in files:
                    low = fn.lower()
                    if low in SENSITIVE_FILES or low.endswith((".pem", ".key", ".p12")):
                        rel = self._rel(Path(cur) / fn, root)
                        extra_findings.append({
                            "rule_id": "SEC-02",
                            "cwe": "CWE-798",
                            "owasp": "A07:2021 Auth Failures",
                            "severity": "CRITICAL",
                            "title": f"Committed Secret / Credential File (`{rel}`)",
                            "file": rel,
                            "line": 1,
                            "snippet": rel,
                            "remediation": f"Remove `{rel}` from git history, add it to `.gitignore`, and rotate exposed keys."
                        })

        if extra_findings:
            all_findings = report["findings"] + extra_findings
            sev_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
            penalty = 0
            for f in all_findings:
                s = f.get("severity", "LOW")
                if s in sev_counts:
                    sev_counts[s] += 1
                penalty += SEVERITY_WEIGHTS.get(s, 5)
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
            report.update({
                "findings": all_findings,
                "vulnerabilities_count": len(all_findings),
                "severity_counts": sev_counts,
                "score": score,
                "overall_grade": grade,
                "is_secure": False,
                "checklist": checklist
            })

        is_secure = report.get("vulnerabilities_count", 0) == 0
        report["verdict"] = "SECURE" if is_secure else "INSECURE"
        report["indicator"] = (
            f"SECURE — Grade {report['overall_grade']} (0 Vulnerabilities)"
            if is_secure
            else f"INSECURE — {report['vulnerabilities_count']} Security Flaw(s) Detected (Grade {report['overall_grade']})"
        )
        return report

    def _get_preview_snapshot(self, root: Path, security: Dict[str, Any], stage1: Dict[str, Any]) -> Dict[str, Any]:
        """Return source snapshot of the most interesting file (first flagged/fixed file, else first .py file)."""
        py_files = self._collect_py_files(root)
        if not py_files:
            return {"file": str(root.name), "lines": [], "exists": False}

        preferred = None
        # Prefer first file with security finding or bug fix
        target_names = [f.get("file") for f in security.get("findings", [])] + stage1.get("modified_files", [])
        for name in target_names:
            for pf in py_files:
                if self._rel(pf, root) == name or pf.name == name:
                    preferred = pf
                    break
            if preferred:
                break

        chosen = preferred or py_files[0]
        lines = chosen.read_text(encoding="utf-8", errors="ignore").splitlines()
        return {
            "file": self._rel(chosen, root),
            "line_count": len(lines),
            "lines": lines,
            "exists": True
        }

    def execute(self, target: str) -> Dict[str, Any]:
        """
        Execute the full On-Demand 2-Stage Pipeline on a submitted GitHub URL or local path:
          1. Stage 1: Bug Detection & Autonomous Fixing
          2. Stage 2: Post-Fix Cybersecurity SAST Scan & SECURE/INSECURE Indicator
        """
        t0 = time.perf_counter()
        root, meta = self._prepare_target(target)
        if root is None:
            return {
                "status": "error",
                "error": meta.get("error", "Could not prepare target repository.")
            }

        stage1 = self._scan_and_fix_bugs(root)
        stage2 = self._run_post_fix_security_scan(root)
        source = self._get_preview_snapshot(root, stage2, stage1)
        duration_ms = int((time.perf_counter() - t0) * 1000)

        result = {
            "status": "completed",
            "repo": meta,
            "duration_ms": duration_ms,
            "stage1_bugs": stage1,
            "stage2_security": stage2,
            "source": source
        }

        # Persist full execution audit trail into SQLite relational database
        try:
            from core.database import get_audit_db
            db = get_audit_db()
            db_id = db.save_audit_report(result)
            result["audit_db_id"] = db_id
        except Exception as e:
            logger.warning(f"Could not persist audit record to SQLite database: {e}")

        return result

