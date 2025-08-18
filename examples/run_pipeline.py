#!/usr/bin/env python3
"""
Simple script to run the DFS pipeline from the examples folder.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from data_collection import run_pipeline

if __name__ == "__main__":
    asyncio.run(run_pipeline()) 