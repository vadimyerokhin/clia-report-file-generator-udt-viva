# Session: Qt Cocoa Platform Plugin Fix
**Date**: 2025-12-12
**Status**: ✅ Completed and pushed to GitHub

## Problem Statement
Application failed to start with error:
```
qt.qpa.plugin: Could not find the Qt platform plugin "cocoa" in ".../PySide6/Qt/plugins/platforms"
This application failed to start because no Qt platform plugin could be initialized.
```

The existing PySide6 health checker reported "healthy" but the GUI would not launch.

## Root Cause Analysis

### Discovery
**File naming mismatch on macOS:**
- PySide6 ships platform plugins as `libqcocoa.dylib` (Unix convention with "lib" prefix)
- Qt's plugin loader expects `cocoa.dylib` (without "lib" prefix)
- Qt's QFactoryLoader **filters out files starting with "libq"** when searching for plugins
- Result: Plugin file exists but is **invisible** to Qt's discovery mechanism

### Why Health Check Previously Passed
The old health check only verified:
- ✅ Module files exist (QtCore, QtWidgets, QtGui)
- ✅ Basic imports work

But it **didn't test QApplication creation**, which is when Qt actually loads platform plugins.

## Solution Implemented

### Enhanced `src/pyside6_health.py`

1. **Platform Plugin Symlink Check** (NEW)
   - Auto-detects missing symlinks on macOS
   - Creates: `cocoa.dylib → libqcocoa.dylib`
   - Also fixes: `minimal.dylib → libqminimal.dylib`, `offscreen.dylib → libqoffscreen.dylib`

2. **QApplication Creation Test** (IMPROVED)
   - Actually creates QApplication instance in offscreen mode
   - Verifies platform plugin loads successfully
   - Catches issues that basic imports miss

### Key Code Pattern
```python
def _check_platform_symlinks(self) -> bool:
    """Check and create platform plugin symlinks on macOS."""
    plugins_dir = Path(PySide6.__file__).parent / "Qt" / "plugins" / "platforms"
    
    symlink_mappings = {
        "cocoa.dylib": "libqcocoa.dylib",
        "minimal.dylib": "libqminimal.dylib",
        "offscreen.dylib": "libqoffscreen.dylib",
    }
    
    for symlink_name, target_name in symlink_mappings.items():
        symlink_path = plugins_dir / symlink_name
        target_path = plugins_dir / target_name
        
        if target_path.exists() and not symlink_path.exists():
            symlink_path.symlink_to(target_name)
```

## Files Modified

| File | Change |
|------|--------|
| `src/pyside6_health.py` | Enhanced with symlink auto-creation and QApplication test |
| `CLAUDE.md` | Updated troubleshooting section with root cause and fix |
| `QT_PLUGIN_FIX_SUMMARY.md` | NEW - Quick reference guide |
| `TROUBLESHOOTING_COCOA_PLUGIN.md` | NEW - Deep technical analysis |
| `pyproject.toml` | Dependency updates |
| `uv.lock` | Lock file sync |

## Git Commit
- **Hash**: `6ac227c`
- **Branch**: `pdf-report-generator`
- **Remote**: `new-origin` (vadimyerokhin/clia-report-file-generator-udt-viva)

## Lessons Learned

### Technical Insights
1. **Qt plugin naming conventions differ from Unix conventions** - Qt expects plugins without "lib" prefix
2. **Health checks must test actual functionality** - Import success ≠ runtime success
3. **Symlinks are the cleanest fix** - No environment variable hacks needed

### Pattern for Future
When health checking any framework with native plugins:
1. Verify files exist
2. Verify imports work
3. **Verify actual instantiation works** (critical!)

## Prevention Checklist
- [x] Health checker now auto-creates symlinks on macOS
- [x] QApplication creation test catches plugin loading failures
- [x] Auto-runs on every GUI startup
- [x] Works across PySide6 reinstalls
- [x] Documented in CLAUDE.md for future reference
