"""Pytest configuration – add project root to sys.path for all tests."""

import sys
from pathlib import Path

# Ensure project root is on sys.path so imports like
# `from config.settings import ...` resolve correctly from the tests/ directory.
sys.path.insert(0, str(Path(__file__).parent))
