# Changelog

All notable changes to the CLIA Report File Generator will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-11-17

### Added
- **Configuration Management**: New `src/config.py` module centralizing all constants (CLIA ID, lab info, PDF settings)
- **Custom Exceptions**: New `src/exceptions.py` with specific exception classes (`DataProcessingError`, `PDFGenerationError`, etc.)
- **Type Hints**: Comprehensive type annotations throughout the codebase for better IDE support and type checking
- **Path Validation**: Security improvements with `validate_path()` and `validate_output_directory()` functions
- **Linting Configuration**:
  - Added `ruff` for fast Python linting with comprehensive rule sets
  - Added `mypy` for static type checking
  - Configured `pyproject.toml` with tool-specific settings
- **CI/CD Pipeline**: GitHub Actions workflow (`.github/workflows/ci.yml`) with:
  - Multi-version Python testing (3.9, 3.10, 3.11)
  - Automated linting and type checking
  - Security scanning with Bandit
  - Code coverage reporting
- **Pre-commit Hooks**: Configuration file for automated code quality checks
- **Development Dependencies**: Added pytest, pytest-cov, coverage, ruff, mypy, and bandit
- **Package Initialization**: Added `src/__init__.py` for proper package structure

### Changed
- **Date Parsing**: Improved date parsing in `main.py` with explicit format specification to eliminate warnings
- **Requirements**: Updated version constraints for better compatibility (Python 3.9+, pandas 2.0+, reportlab 4.0+, PySide6 6.5+)
- **Import System**: Enhanced imports with fallback mechanisms for better module resolution
- **PDF Generator**: Refactored to use centralized configuration constants instead of hardcoded values
- **Code Quality**: Improved code organization, readability, and maintainability throughout

### Fixed
- Date parsing warnings when processing 'Test completed' timestamps
- Path traversal vulnerabilities with proper path validation
- Import issues when running from different directories

### Security
- Added path traversal detection in `validate_path()`
- Added maximum path length validation
- Implemented input sanitization for file paths
- Added Bandit security scanning to CI pipeline

### Documentation
- Added comprehensive CHANGELOG.md
- Enhanced docstrings with Google-style format
- Improved type hints for better code documentation
- Updated README.md with development setup instructions

## [0.1.0] - 2024-XX-XX

### Added
- Initial release
- CSV data processing for CLIA laboratory reports
- PDF generation with reportlab
- GUI interface with PySide6
- Command-line interface
- Test coverage with unittest
- Report organization by date/MRN
- Conflict resolution for duplicate samples
- Positive results summary PDF
- Comprehensive test suite (57 tests)

[0.2.0]: https://github.com/abraxas-scientific/clia-report-file-generator-udt-viva/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/abraxas-scientific/clia-report-file-generator-udt-viva/releases/tag/v0.1.0
