# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python-based laboratory report PDF generator that processes CSV data files and generates professional CLIA-compliant urine drug test reports. Features both CLI and GUI interfaces with intelligent duplicate handling and result filtering.

## Development Commands

### Setup
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Note: coverage package required for testing but not in requirements.txt
pip install coverage
```

### Running the Application

**CLI Mode:**
```bash
python3 src/main.py -i <path_to_csv> -o <output_dir>

# With organization options
python3 src/main.py -i data/Test_Data.csv -o output_reports --organize-by collection-date
# Options: collection-date | tested-date | mrn
```

**GUI Mode:**
```bash
python3 run_gui.py
```

### Testing

```bash
# Run all tests
python3 -m unittest discover tests

# Run specific test file
python3 -m unittest tests.test_data_processor

# Test with coverage
coverage run -m unittest discover tests
coverage report -m

# Generate HTML coverage report
coverage html
```

### Direct Module Testing
```bash
# Test data processor directly
python3 src/data_processor.py

# Test PDF generation directly
python3 src/pdf_generator.py
```

## Architecture Overview

### Core Workflow Pattern
The application follows a pipeline architecture: **Data Ingestion → Validation → Grouping → Conflict Resolution → PDF Generation → Summary**

### Module Responsibilities

**main.py** - Orchestration layer
- Entry point for CLI
- `generate_reports()`: Core generation logic used by both CLI and GUI
- Handles conflict resolution via injectable `conflict_handler` callback
- Manages progress reporting via injectable `progress_callback`
- Coordinates between data processor and PDF generator

**data_processor.py** - Data layer
- `load_and_process_data()`: CSV ingestion, validation, filtering
- Validates required columns at load time
- Filters for Type='Patient' records only
- Groups data by (MR#, Date collected) for unique patient samples
- Returns pandas GroupBy object for iteration

**pdf_generator.py** - Presentation layer
- `generate_pdf_report()`: Individual patient report generation using reportlab
- `generate_positives_summary_pdf()`: Aggregate positive results report
- Filters test results to only 'Positive' or 'Negative' values
- Logs filtered-out results and positive results to RunSummary
- Component functions: `get_lab_header()`, `get_report_title()`, `get_info_tables()`, `get_results_table()`, `get_footer()`, `get_conditional_note()`

**run_summary.py** - Telemetry layer
- `RunSummary` class: Centralized statistics and error tracking
- Collects: successful PDFs, failures, skipped samples, invalid results, positive results
- Configurable output stream for GUI integration
- `print_summary()`: Formatted execution report with emoji indicators

**gui.py** - UI layer (PySide6)
- `MainWindow`: Main application window with file selection and organization options
- `Worker`: QThread-based background processor for non-blocking generation
- `SelectSampleDialog`: Modal dialog for duplicate sample conflict resolution
- Uses signal/slot pattern for thread-safe communication

**utils.py** - Utilities
- `sanitize_filename()`: Safe filename generation from patient names

### Key Design Patterns

**Dependency Injection for Extensibility:**
```python
generate_reports(
    input_file, output_dir, organize_by, summary,
    progress_callback=None,     # Injectable for CLI vs GUI
    conflict_handler=None       # Injectable for CLI vs GUI
)
```

**GroupBy-Based Processing:**
Data is grouped by (MR#, Date collected) creating unique patient sample groups. Each group may contain multiple test results for the same visit.

**Duplicate Sample Handling:**
When multiple Sample IDs exist for the same (MR#, Date collected), the application:
1. Detects via `unique_sample_ids = patient_group['ID'].unique()`
2. Invokes conflict_handler callback (CLI prompts user, GUI shows dialog)
3. Returns selected index or None/negative to skip
4. Logs skipped samples to RunSummary

**Result Filtering:**
Only 'Positive' and 'Negative' results (case-insensitive) are included in PDFs. Invalid results are:
- Logged to RunSummary with `log_invalid_result()`
- Excluded from PDF output
- Displayed in final summary report

**Thread-Safe GUI:**
GUI uses QThread + Worker pattern with signals for:
- Progress updates: `progress.emit(message)`
- Conflict resolution: `conflict.emit(mrn, date, ids)` → blocks until `conflict_resolved.emit(choice)`
- Completion: `finished.emit()`

### Data Flow Example
```
CSV File
  → load_and_process_data() [validation, filtering, grouping]
  → grouped_samples (pandas GroupBy)
  → iterate groups
    → detect duplicate Sample IDs
    → conflict_handler() if needed
    → generate_pdf_report()
      → filter valid results
      → log positives to summary
      → create PDF with reportlab
  → generate_positives_summary_pdf()
  → summary.print_summary()
```

## Testing Strategy

Tests mirror the source structure in `tests/` directory:
- **test_data_processor.py**: CSV loading, validation, filtering, grouping
- **test_pdf_generator.py**: PDF generation, report components, layout
- **test_main.py**: End-to-end workflow, conflict resolution, organization options
- **test_result_filtering.py**: Valid/invalid result handling
- **test_run_summary.py**: Statistics tracking, logging, summary formatting
- **test_utils.py**: Filename sanitization

Test data located in `tests/test_data/` directory.

## Important Implementation Details

### Required CSV Columns
```python
['Type', 'ID', 'Date collected', 'Name', 'MR#', 'Date of Birth',
 'Collected by', 'Test completed', 'Test Name', 'Test result']
```

### Organization Options
- `None`: Flat structure - all PDFs in output_dir
- `collection-date`: Subdirectories by collection date (YYYY-MM-DD)
- `tested-date`: Subdirectories by test completion date (YYYY-MM-DD)
- `mrn`: Subdirectories by Medical Record Number (MRN_####)

### PDF Filename Convention
```
{patient_name}_{mrn}_{collection_date}.pdf
Example: John-Doe_12345_2024-03-15.pdf
```

### CLIA Laboratory Information
Laboratory header contains: Therapeutic Life Choices, LLC | CLIA ID: 37D2301589 | Address and contact information | Laboratory Director: Vadim Yerokhin, PhD

This is hardcoded in `get_lab_header()` - update there if laboratory details change.

### Date Handling Edge Cases
- Collection dates parsed with `pd.to_datetime()`
- Test completion uses `max()` of all test timestamps in sample group
- Fallback to "unknown-date" on parse errors, logged to summary
- Display format: MM/DD/YYYY for PDFs, YYYY-MM-DD for filenames

## Common Development Patterns

### Adding New Test Coverage
1. Create test file matching module name: `test_{module}.py`
2. Place in `tests/` directory
3. Use `unittest.TestCase` base class
4. Follow existing pattern: setup test data, call function, assert results
5. Mark untestable code with `# pragma: no cover` (e.g., `if __name__ == '__main__'` blocks)

### Modifying PDF Layout
All PDF components are in `pdf_generator.py` as separate functions:
- Header: `get_lab_header()` - laboratory identification
- Title: `get_report_title()` - report type
- Patient info: `get_info_tables()` - demographics and specimen details
- Results: `get_results_table()` - test outcomes
- Footer: `get_footer()` - result interpretation text
- Conditional note: `get_conditional_note()` - positive result indicator

### Adding New Organization Options
1. Add option to argparse choices in `main.py`
2. Add radio button in GUI (`src/gui.py`)
3. Implement subdirectory logic in `generate_reports()` organize_by section
4. Update `get_organization_option()` in GUI

### Extending Conflict Resolution
Current system uses callback pattern. To add new resolution strategies:
1. Create handler function: `def handler(mrn, date_collected, unique_sample_ids) -> Optional[int]`
2. Pass to `generate_reports()` as `conflict_handler` parameter
3. Return 0-based index for selection, None/negative to skip
