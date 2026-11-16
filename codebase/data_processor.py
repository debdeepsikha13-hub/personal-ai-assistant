"""
General Python Data Processing & Business Logic Module.
========================================================
A representative codebase module used by Wolf to demonstrate
autonomous bug hunting, traceback diagnosis, code patching, and QA verification.
"""

from typing import List, Dict, Any, Optional


class DataProcessor:
    """Universal data processing engine with aggregation, filtering, and validation."""

    @staticmethod
    def calculate_average(numbers: List[float]) -> float:
        """
        Calculates the arithmetic mean of a list of numbers safely.
        Must handle empty lists without crashing with ZeroDivisionError.
        """
        if not numbers:
            return 0.0
        return round(sum(numbers) / len(numbers), 2)

    @staticmethod
    def filter_active_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filters a list of record dicts to keep only active, verified items.
        Must handle missing keys safely without KeyError.
        """
        if not records:
            return []
        return [r for r in records if r.get("status") == "active" and r.get("verified", False)]

    @staticmethod
    def calculate_percentage_growth(initial: float, current: float) -> float:
        """
        Calculates percentage growth between two numeric values safely.
        Must handle initial == 0 without ZeroDivisionError.
        """
        if initial == 0:
            return 100.0 if current > 0 else 0.0
        growth = ((current - initial) / initial) * 100
        return round(growth, 2)

    @staticmethod
    def safe_divide(numerator: float, denominator: float, fallback: float = 0.0) -> float:
        """Safe division utility avoiding division-by-zero crashes."""
        if denominator == 0:
            return fallback
        return round(numerator / denominator, 4)

    @staticmethod
    def parse_user_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates and sanitizes incoming user dictionary payloads.
        Ensures email is lowercase and name is stripped.
        """
        if not isinstance(payload, dict):
            raise TypeError("Payload must be a dictionary.")

        name = str(payload.get("name", "")).strip()
        email = str(payload.get("email", "")).strip().lower()
        score = float(payload.get("score", 0.0))

        if not email or "@" not in email:
            raise ValueError("Invalid email address format.")

        return {
            "name": name,
            "email": email,
            "score": score,
            "is_passing": score >= 50.0
        }
