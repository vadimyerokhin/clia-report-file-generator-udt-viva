# Qt Platform Plugin "cocoa" Error - Root Cause and Solution

## Problem Description

When launching the PySide6 GUI application on macOS, you may encounter:

```
qt.qpa.plugin: Could not find the Qt platform plugin "cocoa" in "/path/to/PySide6/Qt/plugins/platforms"
This application failed to start because no Qt platform plugin could be initialized.
```

## Root Cause

This is a **file naming convention mismatch** between PySide6 packaging and Qt's plugin discovery mechanism on macOS.

### Technical Details

1. **What PySide6 ships:**
   - Platform plugin file: `libqcocoa.dylib` (Unix library naming convention with "lib" prefix)

2. **What Qt expects on macOS:**
   - Platform plugin file: `cocoa.dylib` (without "lib" prefix)

3. **Why this causes failure:**
   - Qt's QPA (Qt Platform Abstraction) plugin factory loader on macOS filters out files starting with "libq" when searching for platform plugins
   - The factory loader specifically looks for files matching `{platform}.dylib`
   - Result: `libqcocoa.dylib` exists but is invisible to Qt's plugin discovery

### Investigation Evidence

The file physically exists and is valid:
```bash
$ ls -lh .venv/lib/python3.12/site-packages/PySide6/Qt/plugins/platforms/
-rwxr-xr-x  1.8M libqcocoa.dylib  # ✓ File exists
```

Qt reports correct plugin path:
```python
from PySide6.QtCore import QLibraryInfo
QLibraryInfo.path(QLibraryInfo.PluginsPath)
# Returns: '/path/to/PySide6/Qt/plugins'  # ✓ Path is correct
```

Plugin can be manually loaded:
```python
from PySide6.QtCore import QLibrary
lib = QLibrary("path/to/libqcocoa.dylib")
lib.load()  # Returns: True  # ✓ File is valid and loadable
```

But Qt's factory loader doesn't see it:
```
qt.core.plugin.factoryloader: checking directory path ".../platforms"
# Missing: "looking at libqcocoa.dylib"
qt.qpa.plugin: Could not find the Qt platform plugin "cocoa"  # ✗ Plugin not discovered
```

## Solution

Create symlinks without the "lib" prefix so Qt's plugin loader can find them:

```bash
cd /path/to/PySide6/Qt/plugins/platforms/
ln -s libqcocoa.dylib cocoa.dylib
ln -s libqminimal.dylib minimal.dylib
ln -s libqoffscreen.dylib offscreen.dylib
```

### Automated Fix

The `pyside6_health.py` module now **automatically detects and fixes** this issue:

```python
from src.pyside6_health import check_and_repair_pyside6

# This will auto-create symlinks if missing
if not check_and_repair_pyside6():
    print("Failed to repair PySide6")
    sys.exit(1)
```

Health checker output when fixing:
```
🔍 Checking PySide6 installation health...
🔗 Created symlink: cocoa.dylib → libqcocoa.dylib
🔗 Created symlink: minimal.dylib → libqminimal.dylib
🔗 Created symlink: offscreen.dylib → libqoffscreen.dylib
✅ Fixed Qt platform plugin symlinks for macOS
✅ PySide6 installation is healthy
```

## Prevention Checklist

### When Installing PySide6
```bash
# After installing PySide6
pip install pyside6
# or
uv pip install pyside6

# Run health check to auto-fix
python src/pyside6_health.py
```

### For Fresh Virtual Environments
The application's `run_gui.py` automatically runs the health check on startup, so manual intervention is rarely needed.

### After PySide6 Reinstallation
If you reinstall PySide6:
```bash
uv pip install pyside6 --reinstall
python src/pyside6_health.py  # Auto-fixes symlinks
```

## Verification

Verify the fix is in place:

```bash
# Check if symlinks exist
ls -lah /path/to/PySide6/Qt/plugins/platforms/ | grep cocoa

# Should show:
lrwxr-xr-x  cocoa.dylib -> libqcocoa.dylib
-rwxr-xr-x  libqcocoa.dylib
```

Test QApplication creation:
```bash
.venv/bin/python -c "
from PySide6.QtWidgets import QApplication
import sys
app = QApplication(sys.argv)
print(f'✅ Platform: {app.platformName()}')
"

# Should output: ✅ Platform: cocoa
```

## Why Health Check Previously Passed

The old health check only verified:
1. ✅ PySide6 module files exist (QtCore.abi3.so, QtGui.abi3.so, etc.)
2. ✅ Basic imports work (`from PySide6.QtCore import QThread`)

But it **didn't test QApplication creation**, which is when Qt loads platform plugins. The plugin file existed, so file checks passed, but the naming issue prevented Qt from finding it.

### Updated Health Check

Now includes:
1. ✅ Module file existence check
2. ✅ **Platform plugin symlink check and auto-fix** (NEW)
3. ✅ **QApplication creation test** (IMPROVED - catches plugin issues)

## Related Issues

- PySide6 Issue: Plugin naming on macOS doesn't match Qt expectations
- Qt Behavior: QPA plugin factory loader on macOS has specific naming requirements
- Workaround: Symlinks satisfy both Unix library conventions and Qt's discovery mechanism

## Implementation Details

### Health Checker Enhancement

The `_check_and_fix_platform_plugin_symlinks()` method:
- Only runs on macOS (checks `platform.system() == "Darwin"`)
- Locates `PySide6/Qt/plugins/platforms/` directory
- For each platform plugin (`libq*.dylib`), creates corresponding symlink without "lib" prefix
- Handles existing symlinks gracefully (checks if already correct)
- Reports all fixes performed

### QApplication Test Enhancement

The `_can_import_pyside6()` method now:
- Creates a QApplication instance (not just imports)
- Verifies platform plugin loaded successfully
- Detects platform name (should be "cocoa" on macOS)
- Runs in subprocess to avoid polluting main process

## File Locations

- **Health Checker**: `src/pyside6_health.py`
- **GUI Entry Point**: `run_gui.py` (calls health checker on startup)
- **Plugin Directory**: `.venv/lib/python3.12/site-packages/PySide6/Qt/plugins/platforms/`

## Documentation

This issue is documented in:
- `TROUBLESHOOTING_COCOA_PLUGIN.md` (this file) - Detailed technical analysis
- `CLAUDE.md` - Project documentation updated with troubleshooting reference
- `src/pyside6_health.py` - Inline code comments explaining the fix

---

**Last Updated**: 2025-12-12
**Affected Platforms**: macOS (Darwin)
**PySide6 Versions**: 6.10.x (may affect other versions)
**Fix Status**: ✅ Automated in pyside6_health.py
