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

# Add project root to path to support module imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import and run the GUI using module syntax
from src.gui import main

if __name__ == '__main__':
    main()
