#!/usr/bin/env python3
"""
This script serves as the graphical user interface (GUI) entry point for the
PDF Laboratory Report Generator application.

To run the GUI, execute this script from the command line:
    python3 run_gui.py
"""
import sys
from PySide6.QtWidgets import QApplication
from src.gui import MainWindow

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())