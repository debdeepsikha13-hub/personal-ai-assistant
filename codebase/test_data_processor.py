"""
Automated Test Suite for General Codebase Quality & Safety.
===========================================================
Validates 6 universal coding rules: arithmetic, zero-division protection,
dictionary key safety, null checks, boundary limits, and input validation.
"""

import unittest
from codebase.data_processor import DataProcessor


class TestCodebaseQuality(unittest.TestCase):
    """6-Point Quality Assurance Checklist for Code Safety."""

    def test_checklist_1_average_calculation(self):
        """[CHECKLIST-1] Calculate average of numbers accurately."""
        nums = [10.0, 20.0, 30.0, 40.0]
        self.assertEqual(DataProcessor.calculate_average(nums), 25.0)

    def test_checklist_2_empty_list_zero_division_guard(self):
        """[CHECKLIST-2] Empty list must return 0.0 without ZeroDivisionError crash."""
        self.assertEqual(DataProcessor.calculate_average([]), 0.0)

    def test_checklist_3_safe_divide_zero_guard(self):
        """[CHECKLIST-3] Safe divide must return fallback when denominator is 0."""
        self.assertEqual(DataProcessor.safe_divide(100.0, 0.0), 0.0)
        self.assertEqual(DataProcessor.safe_divide(10.0, 2.0), 5.0)

    def test_checklist_4_record_filter_missing_key_safety(self):
        """[CHECKLIST-4] Record filtering must not crash on missing status/verified keys."""
        records = [
            {"id": 1, "status": "active", "verified": True},
            {"id": 2, "status": "inactive"},
            {"id": 3},  # completely missing keys
        ]
        active = DataProcessor.filter_active_records(records)
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["id"], 1)

    def test_checklist_5_percentage_growth_zero_baseline(self):
        """[CHECKLIST-5] Growth calculation must handle zero baseline without division error."""
        self.assertEqual(DataProcessor.calculate_percentage_growth(0.0, 50.0), 100.0)
        self.assertEqual(DataProcessor.calculate_percentage_growth(100.0, 150.0), 50.0)

    def test_checklist_6_user_payload_validation(self):
        """[CHECKLIST-6] Validates email format and normalizes string inputs."""
        payload = {"name": "  Alex Dev  ", "email": "ALEX@TEST.COM", "score": 85.5}
        result = DataProcessor.parse_user_payload(payload)
        self.assertEqual(result["name"], "Alex Dev")
        self.assertEqual(result["email"], "alex@test.com")
        self.assertTrue(result["is_passing"])

        with self.assertRaises(ValueError):
            DataProcessor.parse_user_payload({"name": "No Email", "email": "invalid_email"})


if __name__ == "__main__":
    unittest.main()

