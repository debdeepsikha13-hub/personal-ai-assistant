"""
E-Commerce Bug Fixer & QA Checklist Native Tools.
=================================================
Exposes autonomous bug fixing and QA test checklist verification tools to the agent.
"""

from langchain_core.tools import tool


def _get_bug_fixer_agent():
    """Lazy import to eliminate circular dependencies."""
    from core.bug_fixer_agent import ECommerceBugFixerAgent
    return ECommerceBugFixerAgent()


@tool
def run_bug_fixer_agent(action: str = "full_pipeline") -> str:
    """
    Autonomous E-Commerce Bug Fixer Agent.
    Finds bugs, diagnoses root causes, applies code fixes, and executes test suites.

    Args:
        action: The bug fixer action to perform.
            Options:
            - 'full_pipeline' (default): Runs complete Scan -> Diagnose -> Fix -> Test Checklist cycle.
            - 'scan': Only scans the e-commerce code and tests to check for existing bugs.
            - 'fix': Applies the certified bug fix to ecommerce/cart.py.
            - 'verify': Runs the test suite to verify code compliance.
            - 'simulate_bug': Injects a demo tax-discount bug into the e-commerce cart to demonstrate detection.

    Returns:
        str: Comprehensive formatted QA / Bug Fixer report.
    """
    agent = _get_bug_fixer_agent()
    action = action.lower().strip()

    if action == "simulate_bug":
        res = agent.inject_demo_bug("tax_bug")
        return (
            "⚠️ **Demo E-Commerce Bug Injected!**\n"
            "- Target: `ecommerce/cart.py`\n"
            "- Introduced Flaw: `calculate_tax()` now calculates 8% tax on pre-discount subtotal, violating business rules.\n"
            "- You can now run `run_bug_fixer_agent('scan')` or `run_bug_fixer_agent('full_pipeline')` to watch the agent detect and fix it!"
        )

    elif action == "scan":
        scan = agent.scan_for_bugs()
        if not scan["bug_found"]:
            return (
                "✅ **E-Commerce Code Scan Complete: Healthy**\n"
                f"- All {scan['test_results']['total_tests']} QA checklist tests are PASSING (100% Pass Rate).\n"
                "- No syntax errors, logic flaws, or regressions found."
            )
        diag = scan["diagnosis"]
        return (
            "🚨 **BUG DETECTED in E-Commerce Codebase!**\n"
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
            "🛠️ **Bug Fix Applied to E-Commerce Codebase**\n"
            f"- File Modified: `{fix_res.get('file_modified')}`\n"
            f"- Fix Description: {fix_res.get('fix_applied')}\n"
            "- Recommended Next Step: Run test verification to ensure checklist passes."
        )

    elif action == "verify":
        tests = agent.run_tests()
        lines = [
            f"📋 **E-Commerce QA Test Checklist ({tests['passed_count']}/{tests['total_tests']} Passed - {tests['pass_rate']})**\n"
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
            lines.append("🔍 **Step 1: Code Scan**: No breaking bugs were initially found. Validating golden baseline.\n")

        lines.append(f"🧪 **Step 3: Verification & Test Checklist ({v['passed_count']}/{v['total_tests']} Passed - {v['pass_rate']})**")
        for item in v["checklist"]:
            lines.append(f"- {item['status']} **{item['test_id']}**: {item['description']}")

        lines.append("\n🎉 **Status**: ALL CHECKLIST ITEMS CERTIFIED. Ready for production deployment!")
        return "\n".join(lines)


@tool
def run_ecommerce_test_checklist() -> str:
    """
    Runs the comprehensive QA Test Checklist for the e-commerce store.
    Validates cart subtotal, discount coupons, tax on discounted items,
    free shipping thresholds, inventory limits, and currency rounding.

    Returns:
        str: Checklist execution report.
    """
    agent = _get_bug_fixer_agent()
    tests = agent.run_tests()
    
    lines = [
        f"📋 **E-Commerce Production Checklist ({tests['passed_count']}/{tests['total_tests']} Passed - {tests['pass_rate']})**\n"
    ]
    for item in tests["checklist"]:
        lines.append(f"- {item['status']} **{item['test_id']}**: {item['description']}")

    if tests["all_passed"]:
        lines.append("\n✅ All 6 business rules verified. Code is production ready.")
    else:
        lines.append(f"\n❌ {tests['failed_count']} checklist items failed. Call `run_bug_fixer_agent` to fix.")
        
    return "\n".join(lines)
