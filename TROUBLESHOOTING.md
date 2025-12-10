# Troubleshooting Guide

## GUI Launch Issues

### "Could not find the Qt platform plugin 'cocoa'" Error

**Symptoms:**
- Error appears after terminal restart or system sleep
- Error message: `qt.qpa.plugin: Could not find the Qt platform plugin "cocoa" in ""`
- Application fails to start with Qt initialization error
- ModuleNotFoundError for PySide6 components

**Root Cause:**
PySide6 installation can become corrupted after system sleep/restart cycles or failed partial installations. The module metadata shows it as installed, but critical binary files are missing.

**Automatic Repair (New!):**
The application now includes **intelligent auto-repair functionality** that:
1. ✅ Detects corrupted PySide6 installations automatically
2. 🔧 Repairs them without user intervention
3. 🌍 Works cross-platform (macOS, Linux, Windows)

Simply run the application normally:
```bash
uv run python run_gui.py
```

You'll see output like:
```
🔍 Checking PySide6 installation health...
✅ PySide6 installation is healthy
```

Or if corruption is detected:
```
🔍 Checking PySide6 installation health...
⚠️  Missing PySide6 modules: QtCore, QtWidgets
🔧 Starting PySide6 repair...
📦 Using package manager: uv
1️⃣  Uninstalling corrupted packages...
2️⃣  Cleaning leftover files...
3️⃣  Reinstalling PySide6 (this may take a minute)...
4️⃣  Verifying repair...
✅ PySide6 repair successful!
```

**Manual Repair (If Auto-Repair Fails):**

1. **Use the health check tool**:
   ```bash
   # Check only (no auto-repair)
   uv run python src/pyside6_health.py --no-repair

   # Check and repair
   uv run python src/pyside6_health.py
   ```

2. **Manual reinstall**:
   ```bash
   uv pip uninstall pyside6 pyside6-essentials pyside6-addons
   rm -rf .venv/lib/python3.12/site-packages/pyside6*
   uv pip install "pyside6>=6.10.0" --reinstall --no-cache
   ```

3. **Verify the fix**:
   ```bash
   # Test Qt imports
   uv run python -c "from PySide6.QtCore import QThread; print('✓ Qt OK')"
   ```

**Prevention:**
- The `run_gui.py` script automatically checks and repairs PySide6 on startup
- Qt plugin paths are configured automatically
- Using `uv run` commands ensures proper environment setup
- The health checker logs all operations for debugging

### Python Version Issues

**Symptoms:**
- Import errors related to pandas or pytz
- Compatibility warnings during installation

**Solution:**
- Use Python 3.9-3.12 (Python 3.14 not yet fully supported)
- Recreate virtual environment with correct Python version:
  ```bash
  uv venv --python 3.12
  uv sync
  ```

### Virtual Environment Not Found

**Symptoms:**
- `uv: command not found` or module import errors
- Virtual environment not activated

**Solution:**
1. Ensure uv is installed: https://github.com/astral-sh/uv
2. Recreate virtual environment:
   ```bash
   uv venv --python 3.12
   uv sync
   ```

## Development Issues

### Tests Failing

**Check:**
1. Virtual environment is activated or using correct Python
2. All dependencies installed: `uv pip install -e ".[dev]"`
3. Test data files exist in `tests/test_data/`

### Import Errors

**Solution:**
- Ensure project root is in PYTHONPATH or use editable install:
  ```bash
  uv pip install -e .
  ```

## Getting Help

If issues persist after trying these solutions:
1. Check Python version: `python --version`
2. Check uv version: `uv --version`
3. Verify PySide6 installation: `uv pip show pyside6`
4. Review error logs and traceback carefully

For reporting issues, include:
- Operating system and version
- Python version
- PySide6 version
- Full error message and traceback
- Steps to reproduce
