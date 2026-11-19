"""
Autonomous Python Code Bug Fixer, QA Checklist & Security Audit Native Tools.
=============================================================================
Exposes 2-Stage DevSecOps engineering tools:
  Stage 1: Functional bug scanning, diagnosis, autonomous patching, and QA certification.
  Stage 2: OWASP/CWE SAST cybersecurity scanning on every executed codebase.
"""

from typing import Optional
from langchain_core.tools import tool


def _get_bug_fixer_agent(target_path: Optional[str] = None):
    """Lazy import to eliminate circular dependencies."""
    from core.bug_fixer_agent import GeneralCodeBugFixerAgent
    return GeneralCodeBugFixerAgent(target_path=target_path)


def _format_security_summary(sec: dict) -> str:
    """Format Stage 2 SAST cybersecurity summary for chat output."""
    grade = sec.get("overall_grade", "N/A")
    score = sec.get("score", 0)
    vulns = sec.get("vulnerabilities_count", 0)
    files_scanned = sec.get("files_scanned", 0)
    lines = [
        f"🛡️ **Stage 2: Cybersecurity SAST Audit — Grade {grade} ({score}/100)**",
        f"- Files Scanned: `{files_scanned}` | Vulnerabilities Found: **{vulns}**"
    ]
    if vulns == 0:
        lines.append("- ✅ All 6 OWASP/CWE security controls passed (Injection, Secrets, SQLi, Deserialization, Crypto/TLS, Path Safety).")
    else:
        for f in sec.get("findings", [])[:5]:
            lines.append(
                f"- 🚨 **[{f['severity']}] {f['rule_id']} ({f['cwe']})** in `{f['file']}:{f['line']}` — {f['title']}\n"
                f"  - Fix: {f['remediation']}"
            )
    return "\n".join(lines)


@tool
def run_bug_fixer_agent(action: str = "full_pipeline", target_path: str = "") -> str:
    """
    Autonomous DevSecOps Bug Fixer & Security Verification Agent.
    Executes on real Python files or repositories to detect/fix functional bugs and audit cybersecurity.

    Args:
        action: The engineering action to perform.
            Options:
            - 'full_pipeline' (default): Runs complete Stage 1 (Scan -> Diagnose -> Patch -> QA Verify) + Stage 2 (OWASP/CWE Security Audit).
            - 'scan': Scans the target repository/file for failing tests, AST bugs, and security flaws.
            - 'fix': Applies verified patches to resolve detected bugs and unsafe patterns.
            - 'verify': Runs the automated unit test suite and QA checklist.
            - 'security_audit': Runs deep Static Application Security Testing (SAST) against OWASP/CWE rules.
        target_path: Optional local file or repository directory path to analyze (defaults to active workspace target).

    Returns:
        str: Formatted DevSecOps QA & Security Certification report.
    """
    resolved_target = target_path.strip() or None
    if not resolved_target:
        return "⚠️ Please provide a GitHub repository URL or local folder/file path (`target_path`) to execute."
    agent = _get_bug_fixer_agent(target_path=resolved_target)
    action = action.lower().strip()

    if action == "security_audit":
        sec = agent.run_security_audit()
        if sec.get("status") == "error":
            return f"❌ **Security Audit Error**: {sec.get('error')}"
        return _format_security_summary(sec)

    elif action == "scan":
        scan = agent.scan_for_bugs()
        sec = agent.run_security_audit()
        if not scan["bug_found"]:
            header = (
                "✅ **Stage 1 — Codebase Scan Complete: Healthy**\n"
                f"- Target: `{scan.get('target')}`\n"
                f"- All {scan['test_results']['total_tests']} QA checklist tests are PASSING ({scan['test_results']['pass_rate']}).\n"
                "- Zero runtime crashes, syntax flaws, or regressions found."
            )
        else:
            diag = scan["diagnosis"]
            header = (
                "🚨 **Stage 1 — BUG DETECTED in Codebase!**\n"
                f"- **Title**: {diag['bug_title']}\n"
                f"- **File**: `{diag['file']}`\n"
                f"- **Function**: `{diag['function']}`\n"
                f"- **Severity**: {diag['severity']}\n"
                f"- **Impact**: {diag['impact']}\n"
                f"- **Root Cause**: {diag['root_cause']}\n"
                f"- **Recommended Fix**: {diag['recommended_fix']}\n"
                "👉 Run `run_bug_fixer_agent(action='full_pipeline')` to autonomously patch and certify."
            )
        return header + "\n\n" + _format_security_summary(sec)

    elif action == "fix":
        fix_res = agent.apply_fix()
        sec = agent.run_security_audit()
        return (
            "🛠️ **Bug Fix Applied to Codebase**\n"
            f"- File Modified: `{fix_res.get('file_modified')}`\n"
            f"- Fix Description: {fix_res.get('fix_applied')}\n\n"
            + _format_security_summary(sec)
        )

    elif action == "verify":
        tests = agent.run_tests()
        lines = [
            f"📋 **Code Quality Checklist ({tests['passed_count']}/{tests['total_tests']} Passed - {tests['pass_rate']})**\n"
        ]
        for item in tests["checklist"]:
            lines.append(f"- {item['status']} `{item['test_id']}`: {item['description']}")
        return "\n".join(lines)

    else:
        # Full 2-Stage DevSecOps Pipeline: Bug Remediation + Cybersecurity Audit
        result = agent.run_full_pipeline()
        v = result["verification_results"]
        sec = result["security_audit"]

        loop_data = result.get("agent_loop", {})
        loop_count = loop_data.get("total_iterations", 1)
        loop_status = "RESOLVED ✅" if loop_data.get("resolved") else "RETRY / REVIEW ⚠️"

        lines = [
            "🤖 **Autonomous DevSecOps Pipeline Executed (Agent Loop + SAST Audit)**",
            f"- Target: `{result.get('target')}`",
            f"- **Agent Loop**: `{loop_status}` across **{loop_count}** iteration(s) (Find ➔ Understand ➔ Fix ➔ Run & Check)\n"
        ]

        if result["initial_bug_found"]:
            diag = result["diagnosis"]
            lines.append("🔍 **Stage 1A — Bug Detection & Diagnosis**")
            lines.append(f"- **Bug Found**: {diag['bug_title']}")
            lines.append(f"- **Target File**: `{diag['file']}` -> `{diag['function']}`")
            lines.append(f"- **Root Cause**: {diag['root_cause']}")
            lines.append(f"- **Severity**: {diag['severity']}\n")

            lines.append("🛠️ **Stage 1B — Autonomous Patch Applied**")
            lines.append(f"- **Resolution**: {result['fix_applied']['fix_applied']}\n")
        else:
            lines.append("🔍 **Stage 1 — Code Scan**: No breaking functional bugs detected. Validating QA baseline.\n")

        lines.append(f"🧪 **QA Verification ({v['passed_count']}/{v['total_tests']} Passed - {v['pass_rate']})**")
        for item in v["checklist"]:
            lines.append(f"- {item['status']} **{item['test_id']}**: {item['description']}")

        lines.append("\n" + _format_security_summary(sec))

        if v["all_passed"] and sec.get("is_secure"):
            lines.append("\n🎉 **Certification**: ALL QA & CYBERSECURITY GATES PASSED. Code is production-ready!")
        elif not sec.get("is_secure"):
            lines.append("\n⚠️ **Security Gate Warning**: Functional tests passed, but SAST flagged security vulnerabilities requiring remediation.")
        else:
            lines.append("\n⚠️ **QA Gate Warning**: One or more tests require manual review.")
        return "\n".join(lines)


@tool
def run_code_quality_checklist(target_path: str = "") -> str:
    """
    Runs the comprehensive QA Code Quality Checklist on the target codebase.
    Validates arithmetic, zero division handling, dictionary key safety, and input sanitization.

    Args:
        target_path: Optional local repository or file path.

    Returns:
        str: Checklist execution report.
    """
    resolved = target_path.strip() or None
    if not resolved:
        return "⚠️ Please provide a repository folder or Python file path (`target_path`) to run tests."
    agent = _get_bug_fixer_agent(target_path=resolved)
    tests = agent.run_tests()

    lines = [
        f"📋 **Code Quality Production Checklist ({tests['passed_count']}/{tests['total_tests']} Passed - {tests['pass_rate']})**\n"
    ]
    for item in tests["checklist"]:
        lines.append(f"- {item['status']} **{item['test_id']}**: {item['description']}")

    if tests["all_passed"]:
        lines.append("\n✅ All code safety rules verified. Code is production ready.")
    else:
        lines.append(f"\n❌ {tests['failed_count']} checklist items failed. Call `run_bug_fixer_agent` to fix.")

    return "\n".join(lines)


@tool
def execute_repository_link(repo_url_or_path: str) -> str:
    """
    On-Demand 2-Stage Repository Executor.
    Use ONLY when the user provides a GitHub repository URL (e.g. https://github.com/user/repo)
    or local folder/file path to execute.

    Stage 1: Clones/opens the repository, scans for real bugs, and autonomously fixes them.
    Stage 2: Scans the fixed code for cybersecurity vulnerabilities (OWASP Top 10 / CWE)
             and returns a clear SECURE or INSECURE indicator.

    Args:
        repo_url_or_path: GitHub repo URL (https://github.com/owner/repo) or local path.

    Returns:
        str: Formatted 2-stage report (Stage 1 Bugs Fixed + Stage 2 SECURE/INSECURE verdict).
    """
    from core.repo_executor import OnDemandRepoExecutor

    executor = OnDemandRepoExecutor()
    res = executor.execute(repo_url_or_path)
    if res.get("status") != "completed":
        return f"❌ **Execution Failed**: {res.get('error', 'Unknown error')}"

    repo_label = res["repo"]["repo_label"]
    s1 = res["stage1_bugs"]
    s2 = res["stage2_security"]
    is_secure = s2.get("verdict") == "SECURE"

    loop_info = s1.get("agent_loop", {})
    loop_count = loop_info.get("total_iterations", 1)
    loop_status = loop_info.get("status", "RESOLVED")

    lines = [
        f"🚀 **On-Demand Execution Complete — `{repo_label}`** ({res['duration_ms']}ms)",
        f"### {'🟢 SECURITY VERDICT: CODE IS SECURE ✅' if is_secure else '🔴 SECURITY VERDICT: INSECURE — ACTION REQUIRED 🚨'}",
        f"- **Grade**: **{s2['overall_grade']}** ({s2['score']}/100) | **Vulnerabilities**: **{s2['vulnerabilities_count']}**\n",
        "---",
        f"### Stage 1: Autonomous Agent Loop ({loop_status} • {loop_count} iteration(s))",
        f"- **Agent Pipeline**: `1. Find Bug` ➔ `2. Understand Concept` ➔ `3. Apply Fix` ➔ `4. Run & Check` (loops if broken)",
        f"- Python Files Analyzed: `{s1['files_analyzed']}`",
        f"- Bugs Detected: **{s1['bugs_found_count']}** | Auto-Fixed: **{s1['bugs_fixed_count']}** | Needs Manual Review: **{s1['remaining_bugs_count']}**"
    ]

    if s1["fixes_applied"]:
        lines.append("\n**Patches Applied Automatically:**")
        for fx in s1["fixes_applied"][:10]:
            lines.append(f"- 🛠️ `{fx['file']}:{fx['line']}` ({fx['bug_type']}): {fx.get('fix', fx['description'])}")

    if s1["remaining_bugs"]:
        lines.append("\n**Remaining Bugs Flagged for Review:**")
        for rb in s1["remaining_bugs"][:10]:
            lines.append(f"- ⚠️ `{rb['file']}:{rb['line']}` ({rb['bug_type']}): {rb['description']}")

    lines.append("\n---")
    lines.append("### Stage 2: Post-Fix Cybersecurity Scan (OWASP / CWE)")
    if is_secure:
        lines.append("- ✅ **All 6 OWASP/CWE security checks passed.** No injection flaws, leaked secrets, SQLi, or unsafe deserialization detected.")
    else:
        for f in s2.get("findings", [])[:10]:
            lines.append(
                f"- 🚨 **[{f['severity']}] {f['rule_id']} ({f['cwe']})** in `{f['file']}:{f['line']}` — {f['title']}\n"
                f"  - *Fix*: {f['remediation']}"
            )

    return "\n".join(lines)


# Backwards compatibility alias
run_ecommerce_test_checklist = run_code_quality_checklist
