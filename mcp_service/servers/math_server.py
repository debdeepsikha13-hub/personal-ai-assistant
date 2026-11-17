"""
Advanced Statistics & Mathematics MCP Server.
=============================================
A second standalone Model Context Protocol (MCP) server that provides statistical
analysis, prime verification, and combinatorics tools over stdio.

HOW THIS WORKS (MCP):
- Runs as an independent process.
- Any MCP Client can connect and consume its capabilities.
"""

import math
import statistics
from typing import List
from mcp.server.fastmcp import FastMCP

# Initialize Second FastMCP Server
mcp = FastMCP("AdvancedMathServer")


@mcp.tool()
def calculate_statistics(numbers: List[float]) -> str:
    """
    Compute statistical metrics for a list of numbers (mean, median, standard deviation, min, max, sum).
    
    Args:
        numbers: A list of float or int numbers (e.g. [12.5, 45.0, 67.2, 89.1]).
        
    Returns:
        Summary of statistical values.
    """
    if not numbers:
        return "Error: Empty list of numbers provided."

    mean_val = statistics.mean(numbers)
    median_val = statistics.median(numbers)
    stdev_val = statistics.stdev(numbers) if len(numbers) > 1 else 0.0
    min_val = min(numbers)
    max_val = max(numbers)
    total_sum = sum(numbers)

    return (
        f"Statistical Analysis (Count: {len(numbers)}):\n"
        f"- Mean (Average): {mean_val:.4f}\n"
        f"- Median:        {median_val:.4f}\n"
        f"- Std Deviation: {stdev_val:.4f}\n"
        f"- Min Value:     {min_val}\n"
        f"- Max Value:     {max_val}\n"
        f"- Sum:           {total_sum}"
    )


@mcp.tool()
def is_prime(number: int) -> str:
    """
    Determine whether a given integer is a prime number and find its factors if composite.
    
    Args:
        number: Integer to check.
        
    Returns:
        Explanation whether the number is prime or composite.
    """
    if number <= 1:
        return f"{number} is NOT a prime number (primes are integers > 1)."
    if number in (2, 3):
        return f"{number} is a PRIME number."
    if number % 2 == 0:
        return f"{number} is NOT prime (divisible by 2)."

    limit = int(math.isqrt(number)) + 1
    for i in range(3, limit, 2):
        if number % i == 0:
            return f"{number} is NOT prime (divisible by {i})."

    return f"{number} is a PRIME number."


@mcp.tool()
def calculate_factorial(n: int) -> str:
    """
    Compute the factorial of a non-negative integer (n!).
    
    Args:
        n: Non-negative integer (up to 100).
        
    Returns:
        The exact computed factorial value.
    """
    if n < 0:
        return "Factorial is not defined for negative numbers."
    if n > 100:
        return "To prevent massive output, n is limited to 100."

    result = math.factorial(n)
    return f"{n}! = {result}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
