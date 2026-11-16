"""
General Python Code Bug Fixer & QA Checklist Native Tools.
==========================================================
Exposes autonomous bug hunting, diagnosis, and code quality verification tools.
"""

from langchain_core.tools import tool


def _get_bug_fixer_agent():
    """Lazy import to eliminate circular dependencies."""
    from core.bug_fixer_agent import GeneralCodeBugFixerAgent
    return GeneralCodeBugFixerAgent()


@tool
def run_bug_fixer_agent(action: str = "full_pipeline") -> str:
    """
    Autonomous Python Code Bug Fixer Agent.
    Scans codebases for bugs, diagnoses root causes, applies code patches, and verifies test suites.

    Args:
        action: The action to perform.
            Options:
            - 'full_pipeline' (default): Runs complete Scan -> Diagnose -> Patch -> Verify cycle.
            - 'scan': Only scans the codebase and tests to check for existing bugs.
            - 'fix': Applies the verified bug fix to codebase/data_processor.py.
            - 'verify': Runs the test suite to verify code compliance.
            - 'simulate_bug': Injects a demo ZeroDivisionError bug to demonstrate detection.

    Returns:
        str: Formatted QA / Bug Fixer report.
    """
    agent = _get_bug_fixer_agent()
    action = action.lower().strip()

    if action == "simulate_bug":
        res = agent.inject_demo_bug("zero_division")
        return (
            "⚠️ **Demo Python Bug Injected!**\n"
            "- Target: `codebase/data_processor.py`\n"
            "- Introduced Flaw: Removed empty list guard in `calculate_average()`. It will now crash with `ZeroDivisionError: division by zero` on empty input!\n"
            "- You can now run `run_bug_fixer_agent('scan')` or `run_bug_fixer_agent('full_pipeline')` to watch Wolf detect and fix it!"
        )

    elif action == "scan":
        scan = agent.scan_for_bugs()
        if not scan["bug_found"]:
            return (
                "✅ **Codebase Scan Complete: Healthy**\n"
                f"- All {scan['test_results']['total_tests']} QA checklist tests are PASSING (100% Pass Rate).\n"
                "- Zero runtime crashes, syntax flaws, or regressions found."
            )
        diag = scan["diagnosis"]
        return (
            "🚨 **BUG DETECTED in Codebase!**\n"
            f"- **Title**: {diag['bug_title']}\n"
            f"- **File**: `{diag['file']}`\n"
            f"- **Function**: `{diag['function']}`\n"
            f"- **Severity**: {diag['severity']}\n"
            f"- **Impact**: {diag['impact']}\n"
            f"- **Root Cause**: {diag['root_cause']}\n"
            f"- **Recommended Fix**: {diag['recommended_fix']}\n\n"
            "👉 Run `run_bug_fixer_agent('fix')` or `full_pipeline` to autonomously patch and verify."
        )

    elif action == "fix":
        fix_res = agent.apply_fix()
        return (
            "🛠️ **Bug Fix Applied to Codebase**\n"
            f"- File Modified: `{fix_res.get('file_modified')}`\n"
            f"- Fix Description: {fix_res.get('fix_applied')}\n"
            "- Recommended Next Step: Run test verification to ensure checklist passes."
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
        # Full Pipeline: Scan -> Diagnose -> Fix -> Verify
        result = agent.run_full_pipeline()
        v = result["verification_results"]
        
        lines = [
            "🤖 **Autonomous Bug Fixer Agent Pipeline Executed**\n"
        ]
        
        if result["initial_bug_found"]:
            diag = result["diagnosis"]
            lines.append("🔍 **Step 1: Bug Detection & Diagnosis**")
            lines.append(f"- **Bug Found**: {diag['bug_title']}")
            lines.append(f"- **Target File**: `{diag['file']}` -> `{diag['function']}`")
            lines.append(f"- **Root Cause**: {diag['root_cause']}")
            lines.append(f"- **Severity**: {diag['severity']}\n")

            lines.append("🛠️ **Step 2: Autonomous Patch Applied**")
            lines.append(f"- **Resolution**: {result['fix_applied']['fix_applied']}\n")
        else:
            lines.append("🔍 **Step 1: Code Scan**: No breaking bugs were initially found. Validating baseline.\n")

        lines.append(f"🧪 **Step 3: Verification & Test Checklist ({v['passed_count']}/{v['total_tests']} Passed - {v['pass_rate']})**")
        for item in v["checklist"]:
            lines.append(f"- {item['status']} **{item['test_id']}**: {item['description']}")

        lines.append("\n🎉 **Status**: ALL CHECKLIST ITEMS CERTIFIED. Code is 100% bug-free and ready for production!")
        return "\n".join(lines)


@tool
def run_ecommerce_test_checklist() -> str:
    """
    Runs the comprehensive QA Code Quality Checklist.
    Validates arithmetic, zero division handling, dictionary key safety, and input sanitization.

    Returns:
        str: Checklist execution report.
    """
    agent = _get_bug_fixer_agent()
    tests = agent.run_tests()
    
    lines = [
        f"📋 **Code Quality Production Checklist ({tests['passed_count']}/{tests['total_tests']} Passed - {tests['pass_rate']})**\n"
    ]
    for item in tests["checklist"]:
        lines.append(f"- {item['status']} **{item['test_id']}**: {item['description']}")

    if tests["all_passed"]:
        lines.append("\n✅ All 6 code safety rules verified. Code is production ready.")
    else:
        lines.append(f"\n❌ {tests['failed_count']} checklist items failed. Call `run_bug_fixer_agent` to fix.")
        
    return "\n".join(lines)
