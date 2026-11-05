"""
Top-Level Launcher for the Web Frontend.
========================================
Usage:
    python app.py

Starts the Web Application on http://127.0.0.1:8000
"""

import sys
from pathlib import Path

# Ensure root directory is in sys.path
sys.path.insert(0, str(Path(__file__).parent))

from frontend.app import start_server

if __name__ == "__main__":
    start_server(host="127.0.0.1", port=8000)
