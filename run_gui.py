#!/usr/bin/env python3
"""Entry point for the PDF Laboratory Report Generator GUI application.

This script launches the graphical user interface for generating CLIA-compliant
laboratory reports from CSV data.

Usage:
    python3 run_gui.py
    python run_gui.py
    uv run python run_gui.py
    uv run gui
"""
import os
import sys
from pathlib import Path

# Add project root to path to support module imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Fix Qt platform plugin path for macOS to avoid "cocoa" plugin not found errors
# This is especially important when running via `uv run` which doesn't inherit
# all environment variables from an activated virtual environment
try:
    # Find PySide6 location without importing it (to avoid premature Qt initialization)
    import importlib.util
    spec = importlib.util.find_spec("PySide6")
    if spec and spec.origin:
        pyside_location = Path(spec.origin).parent
        qt_root = pyside_location / "Qt"
        plugin_path = qt_root / "plugins"
        lib_path = qt_root / "lib"

        # Set plugin paths if not already configured
        if plugin_path.exists() and not os.environ.get('QT_PLUGIN_PATH'):
            os.environ['QT_PLUGIN_PATH'] = str(plugin_path)
            os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = str(plugin_path / "platforms")

        # Set library path for Qt frameworks on macOS
        if lib_path.exists():
            dyld_path = os.environ.get('DYLD_LIBRARY_PATH', '')
            lib_path_str = str(lib_path)
            if lib_path_str not in dyld_path:
                os.environ['DYLD_LIBRARY_PATH'] = f"{lib_path_str}:{dyld_path}" if dyld_path else lib_path_str

            # Also set DYLD_FRAMEWORK_PATH for framework resolution
            framework_path = os.environ.get('DYLD_FRAMEWORK_PATH', '')
            if lib_path_str not in framework_path:
                os.environ['DYLD_FRAMEWORK_PATH'] = f"{lib_path_str}:{framework_path}" if framework_path else lib_path_str
except (ImportError, AttributeError):
    # PySide6 not installed yet - will fail when trying to import gui
    pass

# Check PySide6 health and auto-repair if needed before importing GUI
# This prevents cryptic import errors from corrupted installations
try:
    from src.pyside6_health import check_and_repair_pyside6

    if not check_and_repair_pyside6(silent=False, auto_repair=True):
        print("\n❌ Failed to repair PySide6 installation.")
        print("Please try manual reinstall:")
        print("  uv pip uninstall pyside6 pyside6-essentials pyside6-addons")
        print("  uv pip install 'pyside6>=6.10.0' --reinstall --no-cache")
        sys.exit(1)
except ImportError:
    # pyside6_health module not available - continue anyway
    # (this shouldn't happen but provides fallback)
    pass

# Import and run the GUI using module syntax
from src.gui import main

if __name__ == '__main__':
    main()
