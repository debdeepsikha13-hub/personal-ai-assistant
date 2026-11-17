"""
Enterprise Static Application Security Testing (SAST) Scanner.
==============================================================
Performs Python AST and pattern-based cybersecurity vulnerability analysis
against OWASP Top 10 and CWE standards.

Detection Rules:
  SEC-01 [CWE-94 / CWE-78]  : Code Injection & OS Command Execution (eval, exec, shell=True, os.system)
  SEC-02 [CWE-798]          : Hardcoded Secrets, API Keys & Credentials
  SEC-03 [CWE-89]           : SQL Injection via Unparameterized Queries
  SEC-04 [CWE-502]          : Insecure Deserialization (pickle, marshal, unsafe yaml.load)
  SEC-05 [CWE-327 / CWE-295]: Weak Cryptography / Hashing (MD5, SHA-1) & Disabled TLS Verification
  SEC-06 [CWE-22 / CWE-400] : Path Traversal, Unsafe Temp Files & Missing Network Timeouts
"""

import ast
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from utils.logger import setup_logger

logger = setup_logger("security_scanner")

SKIP_DIRS = {
    ".git", ".venv", "venv", "env", "__pycache__", "node_modules",
    ".pytest_cache", ".mypy_cache", "dist", "build", ".tox", ".eggs"
}

SEVERITY_WEIGHTS = {
    "CRITICAL": 30,
    "HIGH": 20,
    "MEDIUM": 10,
    "LOW": 5,
}

RULE_CATALOG = [
    {
        "rule_id": "SEC-01",
        "cwe": "CWE-94 / CWE-78",
        "owasp": "A03:2021 Injection",
        "title": "Code & OS Command Injection Guard",
        "description": "Blocks eval(), exec(), os.system(), and subprocess(shell=True) execution sinks."
    },
    {
        "rule_id": "SEC-02",
        "cwe": "CWE-798",
        "owasp": "A07:2021 Auth Failures",
        "title": "Hardcoded Secrets & API Key Detection",
        "description": "Detects embedded API tokens, private keys, and plaintext passwords in source code."
    },
    {
        "rule_id": "SEC-03",
        "cwe": "CWE-89",
        "owasp": "A03:2021 Injection",
        "title": "SQL Injection Prevention",
        "description": "Flags dynamic SQL queries built with f-strings, % formatting, or string concatenation."
    },
    {
        "rule_id": "SEC-04",
        "cwe": "CWE-502",
        "owasp": "A08:2021 Integrity Failures",
        "title": "Safe Deserialization Enforcement",
        "description": "Identifies unsafe pickle/marshal/shelve deserialization and yaml.load() without SafeLoader."
    },
    {
        "rule_id": "SEC-05",
        "cwe": "CWE-327 / CWE-295",
        "owasp": "A02:2021 Cryptographic Failures",
        "title": "Cryptographic & TLS Verification Guard",
        "description": "Flags deprecated MD5/SHA-1 hashing and disabled SSL/TLS certificate verification (verify=False)."
    },
    {
        "rule_id": "SEC-06",
        "cwe": "CWE-22 / CWE-400",
        "owasp": "A01:2021 Broken Access Control",
        "title": "Path Traversal & Resource Safety",
        "description": "Detects path traversal patterns, insecure tempfile.mktemp(), and unbounded HTTP calls without timeouts."
    },
]

# Regex patterns for hardcoded credentials / tokens (SEC-02)
SECRET_PATTERNS = [
    (r"AIza[0-9A-Za-z\-_]{35}", "Google API Key"),
    (r"gsk_[0-9A-Za-z]{20,}", "Groq API Key"),
    (r"sk-[0-9A-Za-z\-_]{20,}", "OpenAI / Anthropic Secret Key"),
    (r"ghp_[0-9A-Za-z]{30,}", "GitHub Personal Access Token"),
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key ID"),
    (r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----", "Embedded Private Key"),
]

SENSITIVE_VAR_NAMES = {
    "password", "passwd", "pwd", "secret", "secret_key", "api_key",
    "apikey", "access_token", "auth_token", "private_key", "db_password",
    "client_secret", "jwt_secret"
}

SQL_KEYWORDS_RE = re.compile(
    r"\b(SELECT|INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM|DROP\s+TABLE)\b",
    re.IGNORECASE
)


def _get_call_name(node: ast.Call) -> str:
    """Resolve full dotted name of an AST Call node (e.g. subprocess.Popen, os.system)."""
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    elif isinstance(func, ast.Attribute):
        parts = [func.attr]
        curr = func.value
        while isinstance(curr, ast.Attribute):
            parts.append(curr.attr)
            curr = curr.value
        if isinstance(curr, ast.Name):
            parts.append(curr.id)
        return ".".join(reversed(parts))
    return ""


def _get_source_line(lines: List[str], lineno: int) -> str:
    """Safely extract 1-indexed source line stripped of leading/trailing whitespace."""
    if 1 <= lineno <= len(lines):
        return lines[lineno - 1].strip()
    return ""


def _compute_grade(score: int) -> str:
    """Convert numerical security score (0-100) to enterprise letter grade."""
    if score >= 98:
        return "A+"
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 65:
        return "C"
    if score >= 45:
        return "D"
    return "F"


class SecurityVulnerabilityScanner:
    """
    Production Python SAST scanner combining AST analysis and secret-pattern scanning.
    """

    def scan_code(self, source_code: str, filename: str = "<inline>") -> Dict[str, Any]:
        """
        Analyze a Python source string and return structured vulnerability findings,
        CWE/OWASP metadata, per-rule checklist status, score, and security grade.
        """
        findings: List[Dict[str, Any]] = []
        lines = source_code.splitlines()

        # 1. Regex pass for high-entropy / structured API secrets (SEC-02)
        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for pattern, secret_label in SECRET_PATTERNS:
                if re.search(pattern, line):
                    findings.append({
                        "rule_id": "SEC-02",
                        "cwe": "CWE-798",
                        "owasp": "A07:2021 Auth Failures",
                        "severity": "CRITICAL",
                        "title": f"Hardcoded {secret_label} Detected",
                        "file": filename,
                        "line": idx,
                        "snippet": stripped[:120],
                        "remediation": "Remove hardcoded credential immediately, rotate the key, and load it from environment variables or a secret manager."
                    })

        # 2. AST structural analysis
        try:
            tree = ast.parse(source_code, filename=filename)
        except SyntaxError as e:
            findings.append({
                "rule_id": "SEC-01",
                "cwe": "CWE-703",
                "owasp": "Code Integrity",
                "severity": "HIGH",
                "title": f"Python SyntaxError prevents full AST security audit: {e.msg}",
                "file": filename,
                "line": e.lineno or 1,
                "snippet": _get_source_line(lines, e.lineno or 1),
                "remediation": "Fix the Python syntax error so full static security analysis can complete."
            })
            return self._build_report(findings, files_scanned=1, target=filename)

        for node in ast.walk(tree):
            # --- Assignments: detect hardcoded passwords/secrets ---
            if isinstance(node, ast.Assign):
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    val = node.value.value.strip()
                    if len(val) >= 6 and not val.startswith(("${", "ENV:", "os.getenv")):
                        for target in node.targets:
                            var_name = ""
                            if isinstance(target, ast.Name):
                                var_name = target.id.lower()
                            elif isinstance(target, ast.Attribute):
                                var_name = target.attr.lower()
                            if var_name in SENSITIVE_VAR_NAMES:
                                # Ignore obvious placeholders
                                lower_val = val.lower()
                                if any(p in lower_val for p in ("your_", "placeholder", "example", "changeme", "xxx", "dummy", "<")):
                                    continue
                                findings.append({
                                    "rule_id": "SEC-02",
                                    "cwe": "CWE-798",
                                    "owasp": "A07:2021 Auth Failures",
                                    "severity": "HIGH",
                                    "title": f"Hardcoded Credential Assigned to `{var_name}`",
                                    "file": filename,
                                    "line": node.lineno,
                                    "snippet": _get_source_line(lines, node.lineno)[:120],
                                    "remediation": f"Load `{var_name}` via `os.getenv(...)` or a vault instead of hardcoding plaintext values."
                                })

            # --- Function Calls ---
            elif isinstance(node, ast.Call):
                call_name = _get_call_name(node)
                lineno = getattr(node, "lineno", 1)
                snippet = _get_source_line(lines, lineno)[:120]

                # SEC-01: eval / exec / os.system / os.popen / subprocess(shell=True)
                if call_name in {"eval", "exec", "builtins.eval", "builtins.exec"}:
                    findings.append({
                        "rule_id": "SEC-01",
                        "cwe": "CWE-94",
                        "owasp": "A03:2021 Injection",
                        "severity": "CRITICAL",
                        "title": f"Arbitrary Code Execution via `{call_name}()`",
                        "file": filename,
                        "line": lineno,
                        "snippet": snippet,
                        "remediation": "Eliminate dynamic code execution. Use `ast.literal_eval()` for safe data parsing or explicit dispatch tables."
                    })

                elif call_name in {"os.system", "os.popen", "commands.getoutput", "commands.getstatusoutput"}:
                    findings.append({
                        "rule_id": "SEC-01",
                        "cwe": "CWE-78",
                        "owasp": "A03:2021 Injection",
                        "severity": "CRITICAL",
                        "title": f"OS Command Injection Sink via `{call_name}()`",
                        "file": filename,
                        "line": lineno,
                        "snippet": snippet,
                        "remediation": "Replace with `subprocess.run([...], shell=False, check=True)` using an argument list."
                    })

                elif call_name.startswith("subprocess."):
                    for kw in node.keywords:
                        if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                            findings.append({
                                "rule_id": "SEC-01",
                                "cwe": "CWE-78",
                                "owasp": "A03:2021 Injection",
                                "severity": "CRITICAL",
                                "title": f"Shell Injection Risk: `{call_name}(..., shell=True)`",
                                "file": filename,
                                "line": lineno,
                                "snippet": snippet,
                                "remediation": "Pass command arguments as a list and set `shell=False`."
                            })

                # SEC-03: SQL Injection inside .execute() / .executemany()
                if call_name.endswith(".execute") or call_name.endswith(".executemany"):
                    if node.args:
                        query_arg = node.args[0]
                        is_dynamic = False
                        if isinstance(query_arg, ast.JoinedStr):
                            is_dynamic = True
                        elif isinstance(query_arg, ast.BinOp) and isinstance(query_arg.op, (ast.Add, ast.Mod)):
                            is_dynamic = True
                        elif isinstance(query_arg, ast.Call) and isinstance(query_arg.func, ast.Attribute) and query_arg.func.attr == "format":
                            is_dynamic = True

                        if is_dynamic and SQL_KEYWORDS_RE.search(snippet):
                            findings.append({
                                "rule_id": "SEC-03",
                                "cwe": "CWE-89",
                                "owasp": "A03:2021 Injection",
                                "severity": "CRITICAL",
                                "title": "SQL Injection via Unparameterized Dynamic Query",
                                "file": filename,
                                "line": lineno,
                                "snippet": snippet,
                                "remediation": "Use parameterized SQL queries (e.g. `cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))`)."
                            })

                # SEC-04: Insecure Deserialization
                if call_name in {"pickle.loads", "pickle.load", "cPickle.loads", "cPickle.load", "marshal.loads", "marshal.load", "shelve.open"}:
                    findings.append({
                        "rule_id": "SEC-04",
                        "cwe": "CWE-502",
                        "owasp": "A08:2021 Integrity Failures",
                        "severity": "HIGH",
                        "title": f"Insecure Deserialization via `{call_name}()`",
                        "file": filename,
                        "line": lineno,
                        "snippet": snippet,
                        "remediation": "Avoid deserializing untrusted binary data with pickle/marshal. Use `json.loads()` with strict schema validation."
                    })

                elif call_name == "yaml.load":
                    has_safe_loader = any(
                        kw.arg == "Loader" and isinstance(kw.value, (ast.Name, ast.Attribute))
                        and ("SafeLoader" in ast.dump(kw.value))
                        for kw in node.keywords
                    )
                    if not has_safe_loader:
                        findings.append({
                            "rule_id": "SEC-04",
                            "cwe": "CWE-502",
                            "owasp": "A08:2021 Integrity Failures",
                            "severity": "HIGH",
                            "title": "Unsafe YAML Deserialization (`yaml.load` without SafeLoader)",
                            "file": filename,
                            "line": lineno,
                            "snippet": snippet,
                            "remediation": "Use `yaml.safe_load()` or explicitly pass `Loader=yaml.SafeLoader`."
                        })

                elif call_name == "yaml.unsafe_load":
                    findings.append({
                        "rule_id": "SEC-04",
                        "cwe": "CWE-502",
                        "owasp": "A08:2021 Integrity Failures",
                        "severity": "CRITICAL",
                        "title": "Arbitrary Object Instantiation via `yaml.unsafe_load()`",
                        "file": filename,
                        "line": lineno,
                        "snippet": snippet,
                        "remediation": "Replace `yaml.unsafe_load()` with `yaml.safe_load()`."
                    })

                # SEC-05: Weak Cryptography & Disabled TLS Verification
                if call_name in {"hashlib.md5", "hashlib.sha1"}:
                    used_for_sec = True
                    for kw in node.keywords:
                        if kw.arg == "usedforsecurity" and isinstance(kw.value, ast.Constant) and kw.value.value is False:
                            used_for_sec = False
                    if used_for_sec:
                        findings.append({
                            "rule_id": "SEC-05",
                            "cwe": "CWE-327",
                            "owasp": "A02:2021 Cryptographic Failures",
                            "severity": "MEDIUM",
                            "title": f"Weak Cryptographic Hash Function `{call_name}()`",
                            "file": filename,
                            "line": lineno,
                            "snippet": snippet,
                            "remediation": "Use SHA-256 (`hashlib.sha256`) for integrity or Argon2/bcrypt/PBKDF2 for password hashing."
                        })

                if call_name.startswith("requests."):
                    for kw in node.keywords:
                        if kw.arg == "verify" and isinstance(kw.value, ast.Constant) and kw.value.value is False:
                            findings.append({
                                "rule_id": "SEC-05",
                                "cwe": "CWE-295",
                                "owasp": "A02:2021 Cryptographic Failures",
                                "severity": "HIGH",
                                "title": "TLS Certificate Verification Disabled (`verify=False`)",
                                "file": filename,
                                "line": lineno,
                                "snippet": snippet,
                                "remediation": "Remove `verify=False` to prevent Man-in-the-Middle (MitM) interception attacks."
                            })
                    # SEC-06: Missing timeout on requests.* calls
                    has_timeout = any(kw.arg == "timeout" for kw in node.keywords)
                    if not has_timeout and call_name in {
                        "requests.get", "requests.post", "requests.put",
                        "requests.delete", "requests.patch", "requests.request"
                    }:
                        findings.append({
                            "rule_id": "SEC-06",
                            "cwe": "CWE-400",
                            "owasp": "A05:2021 Security Misconfiguration",
                            "severity": "LOW",
                            "title": f"Unbounded Network Request `{call_name}()` Missing Timeout",
                            "file": filename,
                            "line": lineno,
                            "snippet": snippet,
                            "remediation": "Always specify an explicit `timeout=` parameter (e.g., `timeout=10`) to prevent thread exhaustion / DoS."
                        })

                if call_name == "ssl._create_unverified_context":
                    findings.append({
                        "rule_id": "SEC-05",
                        "cwe": "CWE-295",
                        "owasp": "A02:2021 Cryptographic Failures",
                        "severity": "HIGH",
                        "title": "Unverified SSL Context Created",
                        "file": filename,
                        "line": lineno,
                        "snippet": snippet,
                        "remediation": "Use `ssl.create_default_context()` with certificate validation enabled."
                    })

                # SEC-06: Path traversal / insecure temp file
                if call_name == "tempfile.mktemp":
                    findings.append({
                        "rule_id": "SEC-06",
                        "cwe": "CWE-377",
                        "owasp": "A01:2021 Broken Access Control",
                        "severity": "MEDIUM",
                        "title": "Insecure Temporary File Creation (`tempfile.mktemp`)",
                        "file": filename,
                        "line": lineno,
                        "snippet": snippet,
                        "remediation": "Use `tempfile.NamedTemporaryFile()` or `tempfile.mkstemp()` to prevent race-condition attacks."
                    })

                if call_name == "open" and node.args:
                    arg0 = node.args[0]
                    if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str) and ".." in arg0.value:
                        findings.append({
                            "rule_id": "SEC-06",
                            "cwe": "CWE-22",
                            "owasp": "A01:2021 Broken Access Control",
                            "severity": "HIGH",
                            "title": "Potential Path Traversal in File Access (`..` in path)",
                            "file": filename,
                            "line": lineno,
                            "snippet": snippet,
                            "remediation": "Resolve and validate paths against a strict base directory using `Path.resolve()`."
                        })

        return self._build_report(findings, files_scanned=1, target=filename)

    def scan_file(self, filepath: str) -> Dict[str, Any]:
        """Scan a single Python file on disk."""
        path = Path(filepath)
        if not path.exists() or not path.is_file():
            return {
                "status": "error",
                "error": f"Target file not found: {filepath}",
                "target": str(filepath),
                "files_scanned": 0,
                "vulnerabilities_count": 0,
                "score": 0,
                "overall_grade": "N/A",
                "is_secure": False,
                "severity_counts": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0},
                "checklist": [],
                "findings": []
            }
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            return self.scan_code(content, filename=str(path))
        except Exception as e:
            logger.error(f"Error scanning file {filepath}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "target": str(filepath),
                "files_scanned": 0,
                "vulnerabilities_count": 0,
                "score": 0,
                "overall_grade": "N/A",
                "is_secure": False,
                "severity_counts": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0},
                "checklist": [],
                "findings": []
            }

    def scan_directory(self, dirpath: str) -> Dict[str, Any]:
        """Recursively scan all Python files in a directory/repository."""
        root = Path(dirpath)
        if not root.exists():
            return {
                "status": "error",
                "error": f"Target path not found: {dirpath}",
                "target": str(dirpath),
                "files_scanned": 0,
                "vulnerabilities_count": 0,
                "score": 0,
                "overall_grade": "N/A",
                "is_secure": False,
                "severity_counts": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0},
                "checklist": [],
                "findings": []
            }

        if root.is_file():
            return self.scan_file(str(root))

        all_findings: List[Dict[str, Any]] = []
        files_scanned = 0

        for current_root, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for fname in sorted(files):
                if fname.endswith(".py"):
                    full_path = Path(current_root) / fname
                    rel_path = str(full_path.relative_to(root)).replace("\\", "/")
                    try:
                        content = full_path.read_text(encoding="utf-8", errors="ignore")
                        file_report = self.scan_code(content, filename=rel_path)
                        all_findings.extend(file_report["findings"])
                        files_scanned += 1
                    except Exception as e:
                        logger.warning(f"Skipping unreadable file {full_path}: {e}")

        return self._build_report(all_findings, files_scanned=files_scanned, target=str(root))

    def _build_report(self, findings: List[Dict[str, Any]], files_scanned: int, target: str) -> Dict[str, Any]:
        """Aggregate findings into an executive-ready SAST report."""
        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        triggered_rules = set()
        penalty = 0

        for f in findings:
            sev = f.get("severity", "LOW")
            if sev in severity_counts:
                severity_counts[sev] += 1
            penalty += SEVERITY_WEIGHTS.get(sev, 5)
            triggered_rules.add(f.get("rule_id"))

        score = max(0, 100 - penalty)
        grade = _compute_grade(score)
        is_secure = len(findings) == 0

        checklist = []
        for rule in RULE_CATALOG:
            rid = rule["rule_id"]
            rule_findings = [f for f in findings if f.get("rule_id") == rid]
            passed = len(rule_findings) == 0
            checklist.append({
                "rule_id": rid,
                "cwe": rule["cwe"],
                "owasp": rule["owasp"],
                "title": rule["title"],
                "description": rule["description"],
                "passed": passed,
                "status": "SECURE ✅" if passed else f"FLAGGED ({len(rule_findings)}) ⚠️",
                "findings_count": len(rule_findings)
            })

        return {
            "status": "completed",
            "target": target,
            "files_scanned": files_scanned,
            "vulnerabilities_count": len(findings),
            "score": score,
            "overall_grade": grade,
            "is_secure": is_secure,
            "severity_counts": severity_counts,
            "checklist": checklist,
            "findings": findings
        }
