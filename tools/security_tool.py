"""
Enterprise Cybersecurity SAST Audit Native Tool.
================================================
Exposes Wolf's OWASP Top 10 / CWE Static Application Security Testing scanner
directly to the LangGraph agent for on-demand repository and code audits.
"""

from langchain_core.tools import tool


@tool
def run_security_audit(target_path: str = "") -> str:
    """
    Executes an OWASP Top 10 / CWE Static Application Security Testing (SAST) scan
    on a local Python file or repository directory.

    Detects:
      - SEC-01 [CWE-94/78]: Code & OS Command Injection (eval, exec, os.system, shell=True)
      - SEC-02 [CWE-798]: Hardcoded Secrets, API Keys, and Plaintext Passwords
      - SEC-03 [CWE-89]: SQL Injection via dynamic unparameterized queries
      - SEC-04 [CWE-502]: Insecure Deserialization (pickle, marshal, unsafe yaml.load)
      - SEC-05 [CWE-327/295]: Weak Cryptography (MD5/SHA-1) and disabled TLS verification
      - SEC-06 [CWE-22/400]: Path Traversal, insecure temp files, and missing HTTP timeouts

    Args:
        target_path: Optional local file or repository directory path to audit.
                     Defaults to the active codebase (`codebase/data_processor.py`).

    Returns:
        str: Formatted cybersecurity grade, CWE checklist, and remediation report.
    """
    from core.bug_fixer_agent import TARGET_FILE_PATH
    from core.security_scanner import SecurityVulnerabilityScanner

    scanner = SecurityVulnerabilityScanner()
    effective_target = target_path.strip() or TARGET_FILE_PATH
    report = scanner.scan_directory(effective_target)

    if report.get("status") == "error":
        return f"❌ **Security Audit Failed**: {report.get('error')}"

    lines = [
        f"🛡️ **Cybersecurity SAST Audit Report — Grade {report['overall_grade']} ({report['score']}/100)**",
        f"- **Target**: `{report['target']}`",
        f"- **Files Scanned**: `{report['files_scanned']}` | **Vulnerabilities Found**: `{report['vulnerabilities_count']}`",
        f"- **Severity Breakdown**: CRITICAL: {report['severity_counts']['CRITICAL']} | HIGH: {report['severity_counts']['HIGH']} | MEDIUM: {report['severity_counts']['MEDIUM']} | LOW: {report['severity_counts']['LOW']}\n",
        "### OWASP / CWE Security Controls Checklist"
    ]

    for item in report["checklist"]:
        lines.append(f"- {item['status']} **{item['rule_id']} ({item['cwe']})** — {item['title']}")

    if report["findings"]:
        lines.append("\n### Flagged Security Vulnerabilities & Remediation")
        for idx, f in enumerate(report["findings"][:10], start=1):
            lines.append(
                f"{idx}. **[{f['severity']}] {f['rule_id']} ({f['cwe']} / {f['owasp']})** — {f['title']}\n"
                f"   - Location: `{f['file']}:{f['line']}`\n"
                f"   - Code: `{f['snippet']}`\n"
                f"   - Remediation: {f['remediation']}"
            )
    else:
        lines.append("\n✅ **Zero security vulnerabilities detected.** Target codebase meets enterprise DevSecOps standards.")

    return "\n".join(lines)
