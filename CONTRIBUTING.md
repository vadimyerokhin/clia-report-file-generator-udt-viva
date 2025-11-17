# Contributing to CLIA Report File Generator

Thank you for your interest in contributing to the CLIA Report File Generator! This document provides guidelines and instructions for contributing.

## Development Setup

### Prerequisites
- Python 3.9 or higher
- Git

### Setting Up Your Development Environment

1. **Clone the repository**:
   ```bash
   git clone https://github.com/abraxas-scientific/clia-report-file-generator-udt-viva.git
   cd clia-report-file-generator-udt-viva
   ```

2. **Create a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install pre-commit hooks** (optional but recommended):
   ```bash
   pip install pre-commit
   pre-commit install
   ```

## Code Quality Standards

### Linting and Formatting

We use `ruff` for linting and formatting:

```bash
# Check for issues
ruff check src/ tests/

# Auto-fix issues
ruff check --fix src/ tests/

# Format code
ruff format src/ tests/
```

### Type Checking

We use `mypy` for static type checking:

```bash
mypy src/ --install-types --non-interactive
```

### Testing

All contributions must include tests. We aim for high test coverage:

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run with coverage
python3 -m pytest tests/ --cov=src --cov-report=html

# Run specific test file
python3 -m pytest tests/test_main.py -v
```

### Security Scanning

Run security checks with Bandit:

```bash
bandit -r src/
```

## Coding Guidelines

### Style Guide

- Follow PEP 8 style guidelines
- Use type hints for all function signatures
- Maximum line length: 100 characters
- Use descriptive variable names

### Documentation

- All functions must have docstrings in Google style
- Include type hints in function signatures
- Document exceptions that can be raised
- Update CHANGELOG.md for significant changes

### Example Function

```python
def process_sample(
    sample_id: str,
    data: pd.DataFrame,
    validate: bool = True
) -> Optional[dict[str, Any]]:
    """Processes a laboratory sample and returns results.

    Args:
        sample_id: Unique identifier for the sample.
        data: DataFrame containing the sample data.
        validate: Whether to validate the data before processing.

    Returns:
        Dictionary containing processed results, or None if processing fails.

    Raises:
        DataProcessingError: If the sample data is invalid.
        ValueError: If the sample_id is empty.

    Examples:
        >>> process_sample("S001", sample_df)
        {'id': 'S001', 'status': 'processed'}
    """
    if not sample_id:
        raise ValueError("sample_id cannot be empty")

    # Processing logic here
    ...
```

## Commit Message Guidelines

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting, etc.)
- `refactor:` Code refactoring
- `test:` Adding or updating tests
- `chore:` Maintenance tasks

### Examples

```
feat: Add support for custom date formats
fix: Resolve path traversal vulnerability in file handling
docs: Update README with installation instructions
test: Add tests for PDF generation edge cases
```

## Pull Request Process

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**:
   - Write code following our guidelines
   - Add or update tests
   - Update documentation

3. **Run quality checks**:
   ```bash
   # Run tests
   python3 -m pytest tests/ -v

   # Run linting
   ruff check src/ tests/

   # Run type checking
   mypy src/
   ```

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: your feature description"
   ```

5. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request**:
   - Provide a clear description of the changes
   - Reference any related issues
   - Ensure all CI checks pass

## Testing Guidelines

### Test Structure

- Place tests in the `tests/` directory
- Name test files as `test_*.py`
- Use descriptive test names: `test_function_name_condition_expected_result`

### Test Categories

1. **Unit Tests**: Test individual functions in isolation
2. **Integration Tests**: Test multiple components working together
3. **Edge Cases**: Test boundary conditions and error handling

### Example Test

```python
def test_sanitize_filename_removes_illegal_characters(self):
    """Test that illegal filesystem characters are removed."""
    result = sanitize_filename("file/name:with*illegal?chars")
    self.assertEqual(result, "file-name-with-illegal-chars")
    self.assertNotIn("/", result)
    self.assertNotIn("*", result)
```

## Reporting Issues

When reporting issues, please include:

1. **Description**: Clear description of the problem
2. **Steps to Reproduce**: Detailed steps to reproduce the issue
3. **Expected Behavior**: What you expected to happen
4. **Actual Behavior**: What actually happened
5. **Environment**: Python version, OS, package versions
6. **Logs/Screenshots**: Any relevant error messages or screenshots

## Questions or Need Help?

- Open an issue for bugs or feature requests
- Check existing issues and pull requests first
- Reach out to maintainers for major changes

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on the code, not the person
- Help create a positive environment for all contributors

Thank you for contributing to make this project better!
