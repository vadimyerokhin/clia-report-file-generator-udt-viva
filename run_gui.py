#!/usr/bin/env python3
"""Entry point for the PDF Laboratory Report Generator GUI application.

This script launches the graphical user interface for generating CLIA-compliant
laboratory reports from CSV data.

Usage:
    python3 run_gui.py
    python run_gui.py
"""
import sys
from pathlib import Path

# Add src directory to path to support imports
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

# Import and run the GUI
from gui import main

if __name__ == '__main__':
    main()
