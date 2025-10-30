# GUI Enhancements - Persistent Configuration & UX Improvements

## Overview

This document describes the comprehensive GUI enhancements implemented to provide a world-class user experience with persistent configuration across sessions.

## Changes Summary

### 1. Fixed Entry Point Issue

**Problem**: Users had to run `python src/gui.py` instead of `python run_gui.py` due to import path issues.

**Solution**:
- Modified `run_gui.py` to properly add `src/` to Python path
- Updated `src/gui.py` with try/except import fallback for both project root and direct execution
- Added proper `main()` function in `src/gui.py` that can be called from external entry points

**Result**: Both entry points now work correctly:
```bash
python3 run_gui.py          # Works from project root
python3 src/gui.py          # Works when running directly
```

### 2. Persistent Configuration System

**New Component**: `src/config_manager.py`

A comprehensive configuration management system that:
- Saves and loads user preferences automatically
- Provides cross-platform support (Windows, macOS, Linux)
- Handles corrupted configuration files gracefully
- Uses atomic file writes to prevent data corruption
- Validates all configuration values

**Configuration Storage Locations**:
- **macOS**: `~/Library/Application Support/clia-report-generator/config.json`
- **Linux**: `~/.config/clia-report-generator/config.json`
- **Windows**: `%APPDATA%\clia-report-generator\config.json`

**Saved Settings**:
```json
{
  "last_input_file": "/path/to/last/file.csv",
  "last_output_dir": "/path/to/output",
  "organization_option": "collection-date",
  "generate_positive_summary": true,
  "window_geometry": {
    "width": 1200,
    "height": 800,
    "x": 100,
    "y": 100
  },
  "recent_input_files": ["/path/to/file1.csv", "/path/to/file2.csv"],
  "recent_output_dirs": ["/path/to/dir1", "/path/to/dir2"],
  "max_recent_items": 10,
  "show_welcome": true
}
```

**Key Features**:
- **Auto-save on close**: Settings automatically saved when window closes
- **Auto-save on generation**: Settings saved before starting report generation
- **Validation**: All loaded configuration is validated and corrected if invalid
- **Recent files/directories**: Automatically tracks last 10 used files and directories
- **Graceful degradation**: Uses defaults if config file is missing or corrupted

### 3. Enhanced User Interface

#### A. File Selection Improvements

**Before**:
- Basic file/folder selection with read-only text fields
- No drag-and-drop validation
- No recent files access

**After**:
- Drag-and-drop with file type validation
- Recent files dropdown (shows only existing files)
- Recent directories dropdown (shows only existing directories)
- Clear labels and placeholders
- File browser remembers last used directory

#### B. Input Validation

**Real-time validation**:
- Generate button disabled until valid inputs provided
- Status bar shows validation messages
- Visual feedback on invalid paths
- Prevents common user errors

#### C. Enhanced Welcome Screen

**Features**:
- Professional layout with feature list
- "Don't show again" option (persisted)
- Clear call-to-action button
- Informative description

#### D. Improved Progress Tracking

**Enhancements**:
- Clear section headers in log output
- Formatted run summary
- Monospace font for better readability
- Better visual separation of log sections

#### E. Professional Polish

- **Tooltips**: All controls have helpful tooltips
- **Status bar**: Shows real-time status and validation messages
- **Button styling**: Generate button emphasized with bold text
- **Consistent spacing**: Professional 10px spacing throughout
- **Reset settings button**: Allows resetting to defaults
- **Window geometry**: Position and size restored on startup

### 4. UX Workflow

**First Launch**:
1. User runs `python run_gui.py`
2. Welcome screen appears explaining features
3. User can check "Don't show again" to skip in future
4. GUI opens with default settings

**Subsequent Launches**:
1. User runs `python run_gui.py`
2. GUI opens with last used settings pre-loaded:
   - Last input file (if still exists)
   - Last output directory (if still exists)
   - Organization preference
   - Positive summary checkbox state
   - Window size and position
3. Recent files/directories available in dropdowns
4. User can immediately start working or adjust settings

**During Use**:
1. User selects input file (via browse, drag-drop, or recent list)
2. User selects output directory (via browse, drag-drop, or recent list)
3. Generate button enables when both inputs valid
4. User adjusts organization and summary options as needed
5. Click "Generate Reports"
6. Settings automatically saved
7. Progress tracked in real-time
8. PDF preview updates as reports generated

**On Close**:
1. Current settings automatically saved
2. Window position and size saved
3. Ready for next launch

### 5. Testing

**New Test Suite**: `tests/test_config_manager.py`

Comprehensive tests covering:
- Default configuration values
- Save and load operations
- Get/set/update methods
- Reset to defaults functionality
- Recent files/directories management
- Duplicate handling
- Max items limiting
- Filtering non-existent paths
- Configuration validation
- Corrupted file handling
- Missing file handling
- Atomic saves
- Cross-platform compatibility

**Test Results**: All 23 tests passing

```bash
# Run tests
python3 tests/test_config_manager.py

# Expected output:
# .......................
# Ran 23 tests in 0.014s
# OK
```

## API Reference

### ConfigManager Class

```python
from config_manager import ConfigManager

# Initialize
config_manager = ConfigManager()

# Load configuration
config = config_manager.load_config()

# Get value
value = config_manager.get("key", default="default_value")

# Set value
config_manager.set("key", "value")

# Update multiple values
config_manager.update({
    "last_input_file": "/path/to/file.csv",
    "organization_option": "mrn"
})

# Save configuration
config_manager.save_config()

# Add to recent files
config_manager.add_recent_file("/path/to/file.csv")
config_manager.add_recent_dir("/path/to/directory")

# Get recent lists (filtered to existing paths)
recent_files = config_manager.get_recent_files()
recent_dirs = config_manager.get_recent_dirs()

# Reset to defaults
config_manager.reset_to_defaults()

# Get config file path
path = config_manager.get_config_path()
```

## Migration Notes

**From Previous Version**:
- No migration needed - first launch creates new config with defaults
- Users will need to re-select their preferred settings on first launch after update
- Previous workflow remains unchanged, just enhanced

**Backward Compatibility**:
- All existing functionality preserved
- New features are additive only
- No breaking changes to API or workflow

## Configuration File Format

The configuration file is stored in JSON format for easy reading and editing:

```json
{
  "last_input_file": "/path/to/data.csv",
  "last_output_dir": "/path/to/output",
  "organization_option": "collection-date",
  "generate_positive_summary": true,
  "window_geometry": {
    "width": 1200,
    "height": 800,
    "x": 100,
    "y": 100
  },
  "recent_input_files": [
    "/path/to/recent1.csv",
    "/path/to/recent2.csv"
  ],
  "recent_output_dirs": [
    "/path/to/output1",
    "/path/to/output2"
  ],
  "max_recent_items": 10,
  "show_welcome": false
}
```

**Valid Values**:
- `organization_option`: "none", "collection-date", "tested-date", "mrn"
- `generate_positive_summary`: true or false
- `show_welcome`: true or false
- `max_recent_items`: any positive integer (default: 10)

**Manual Editing**:
Users can manually edit the configuration file if needed. Invalid values will be automatically corrected on next load.

## Troubleshooting

### Configuration Issues

**Problem**: Settings not persisting
**Solution**: Check file permissions on config directory

**Problem**: Corrupted configuration
**Solution**: Delete config file - will regenerate with defaults on next launch

**Problem**: Recent files not showing
**Solution**: Only existing files are shown - deleted files automatically filtered

### Import Issues

**Problem**: ModuleNotFoundError when running
**Solution**: Run from project root: `python3 run_gui.py`

**Problem**: Import errors in tests
**Solution**: Run tests directly: `python3 tests/test_config_manager.py`

## Future Enhancements

Possible future improvements:
- Export/import configuration profiles
- Keyboard shortcuts
- Command-line arguments for batch processing
- Configuration presets (templates)
- Multi-language support
- Dark mode theme
- Custom organization patterns

## Technical Details

### Cross-Platform Support

The configuration manager handles platform-specific paths:

```python
# macOS
config_base = Path.home() / 'Library' / 'Application Support'

# Linux
config_base = Path(os.environ.get('XDG_CONFIG_HOME',
                                  Path.home() / '.config'))

# Windows
config_base = Path(os.environ.get('APPDATA',
                                  Path.home() / 'AppData' / 'Roaming'))
```

### Atomic Saves

Configuration saves use atomic writes to prevent corruption:

```python
# Write to temporary file
temp_file = config_file.with_suffix('.json.tmp')
with open(temp_file, 'w') as f:
    json.dump(config, f)

# Atomic rename (replaces old file)
temp_file.replace(config_file)
```

### Thread Safety

The GUI uses Qt's signal/slot mechanism for thread-safe communication:
- Configuration saved on main thread only
- Background worker doesn't access config directly
- All UI updates through signals

## Performance Considerations

- Configuration loaded once on startup (cached)
- Recent files filtered only when displayed
- Validation only runs when needed
- No performance impact on report generation

## Security Considerations

- Configuration file contains paths only (no sensitive data)
- File permissions respect OS defaults
- No network communication
- No credential storage

## Summary

The enhanced GUI provides a professional, user-friendly experience with:
- Zero configuration required on first launch
- Intelligent defaults that adapt to user preferences
- Persistent settings across sessions
- Robust error handling and validation
- Cross-platform compatibility
- Comprehensive test coverage
- Clean, maintainable code architecture

Users can now focus on generating reports without repeatedly entering settings, while the application remembers their preferences and adapts to their workflow.
