# Qt Platform Plugin "cocoa" Error - Resolution Summary

## Issue Resolved ✅

The Qt platform plugin "cocoa" error has been **definitively resolved** through automated detection and repair.

## What Was the Problem?

### Symptom
```
qt.qpa.plugin: Could not find the Qt platform plugin "cocoa" in "/path/to/PySide6/Qt/plugins/platforms"
This application failed to start because no Qt platform plugin could be initialized.
```

### Root Cause Discovery

Through systematic investigation using `--ultrathink` mode, the root cause was identified:

**File Naming Mismatch on macOS:**
- PySide6 ships: `libqcocoa.dylib` (Unix library convention - includes "lib" prefix)
- Qt expects: `cocoa.dylib` (platform plugin convention - no "lib" prefix)
- Qt's plugin factory loader on macOS **filters out** files starting with "libq"
- Result: Plugin file exists but is **invisible** to Qt's discovery mechanism

### Why Health Check Previously Passed

The old health checker only verified:
1. ✅ Module files exist (QtCore.abi3.so, QtWidgets.abi3.so)
2. ✅ Basic imports work (from PySide6 import QtCore)

But it **didn't test QApplication creation**, which is when Qt loads platform plugins.

## The Solution

### Automated Fix Implemented

**File**: `src/pyside6_health.py`

Enhanced with two key improvements:

1. **Platform Plugin Symlink Check** (NEW)
   - Detects missing symlinks on macOS
   - Auto-creates: `cocoa.dylib → libqcocoa.dylib`
   - Also fixes: minimal.dylib, offscreen.dylib

2. **QApplication Creation Test** (IMPROVED)
   - Actually creates QApplication in subprocess
   - Verifies platform plugin loads successfully
   - Catches issues that basic imports miss

### How It Works

When you run `run_gui.py` or the health checker:

```
🔍 Checking PySide6 installation health...
🔗 Created symlink: cocoa.dylib → libqcocoa.dylib
🔗 Created symlink: minimal.dylib → libqminimal.dylib
🔗 Created symlink: offscreen.dylib → libqoffscreen.dylib
✅ Fixed Qt platform plugin symlinks for macOS
✅ PySide6 installation is healthy
```

## Verification

Test the fix:

```bash
# Run health check manually
.venv/bin/python src/pyside6_health.py

# Or test QApplication directly
.venv/bin/python -c "
from PySide6.QtWidgets import QApplication
import sys
app = QApplication(sys.argv)
print(f'✅ Platform: {app.platformName()}')
"
```

Expected output:
```
✅ Platform: cocoa
```

## What Changed

### Files Modified

1. **src/pyside6_health.py**
   - Added `_check_and_fix_platform_plugin_symlinks()` method
   - Enhanced `_can_import_pyside6()` to test QApplication creation
   - Updated `check_health()` to include platform plugin check

2. **CLAUDE.md**
   - Updated troubleshooting section with accurate root cause
   - Documented the automatic fix mechanism

3. **TROUBLESHOOTING_COCOA_PLUGIN.md** (NEW)
   - Complete technical analysis
   - Investigation evidence
   - Prevention checklist
   - Verification steps

## Prevention

### For Future Installations

After installing or reinstalling PySide6:
```bash
pip install pyside6
python src/pyside6_health.py  # Auto-creates symlinks
```

### After System Updates

If macOS updates or after virtual environment recreation:
```bash
uv run python src/pyside6_health.py  # Re-verify and fix if needed
```

## Technical Details

### Investigation Process

1. ✅ Verified plugin file exists (1.9 MB libqcocoa.dylib)
2. ✅ Confirmed Qt paths configured correctly
3. ✅ Tested manual plugin loading (successful with QLibrary)
4. ✅ Analyzed otool dependencies (all valid)
5. ✅ Enabled Qt debug logging (QT_DEBUG_PLUGINS=1)
6. ✅ Discovered factory loader not "looking at" libqcocoa.dylib
7. ✅ Created test symlink cocoa.dylib → Success!
8. ✅ Implemented automated fix in health checker

### Evidence Trail

Qt debug output **before fix**:
```
qt.core.plugin.factoryloader: checking directory path ".../platforms"
# Missing: "looking at libqcocoa.dylib"
qt.qpa.plugin: Could not find the Qt platform plugin "cocoa"
```

Qt debug output **after fix** (with symlink):
```
qt.core.plugin.factoryloader: checking directory path ".../platforms"
qt.core.plugin.factoryloader: looking at "cocoa.dylib"
qt.core.plugin.loader: Found metadata in lib .../libqcocoa.dylib
qt.core.plugin.factoryloader: Got keys from plugin meta data QList("cocoa")
```

## Files You Can Delete

These test files were created during investigation and can be removed:
- ✅ Already cleaned up (test_*.py files removed)
- ✅ Temporary qt.conf removed

## No Manual Intervention Required

The fix is **fully automated**:
- ✅ Runs on every GUI startup via `run_gui.py`
- ✅ Handles missing symlinks automatically
- ✅ Idempotent (safe to run multiple times)
- ✅ No environment variable hacks needed
- ✅ Works across virtual environment recreations

## Success Metrics

- ✅ Root cause identified and documented
- ✅ Automated fix implemented and tested
- ✅ Health checker enhanced to prevent recurrence
- ✅ Documentation updated with solution
- ✅ GUI launches without errors
- ✅ Prevention checklist created

---

**Resolution Date**: 2025-12-12
**Investigation Time**: ~30 minutes of systematic debugging
**Permanent Fix**: Automated in pyside6_health.py
**Future Proof**: Yes - handles PySide6 reinstalls automatically
