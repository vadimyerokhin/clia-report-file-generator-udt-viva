# Project Architecture Patterns

## Core Design Patterns

### 1. Dependency Injection for CLI/GUI Flexibility
The codebase uses callback-based dependency injection:

```python
def generate_reports(input_file, output_dir, organize_by, summary, 
                    progress_callback=None,    # Injectable
                    conflict_handler=None):    # Injectable
```

**Benefits:**
- Same core logic serves both CLI and GUI
- Enables testability with mock callbacks
- Clean separation of concerns

### 2. GroupBy-Based Data Processing
Patient data grouped by `(MR#, Date collected)` tuple:
```python
grouped_samples = patient_data.groupby(['MR#', 'Date collected'])
```

**Key Insight:**
- Creates unique patient samples
- One patient may have multiple visits
- Each group = all tests for that patient on that date

### 3. RunSummary Telemetry Pattern
Centralized statistics with configurable output:
```python
class RunSummary:
    def __init__(self):
        self.output_stream = sys.stdout  # Configurable
        self._pdfs_generated = 0
        self._billing_entries = 0
```

**Benefits:**
- Single source of truth for stats
- GUI can redirect to StringIO
- Unified summary format

## Threading Architecture (GUI)

### Worker Pattern with Qt Signals
```python
class Worker(QObject):
    progress = Signal(str)
    conflict = Signal(str, str, list)
    
    def run(self):
        generate_reports(..., 
                        progress_callback=self.progress.emit,
                        conflict_handler=self.handle_conflict)
```

**Thread Safety:**
- Worker runs in QThread
- Signal/slot for thread-safe communication
- Conflict resolution blocks until user response

## Data Validation Patterns

### Required vs Optional Fields
```python
# Required field - skip if missing
if not mrn or pd.isna(mrn):
    summary.log_billing_failure("UNKNOWN", "Missing MRN")
    continue

# Optional field - use empty string
if pd.isna(collected_by_value):
    ordering_provider = ''
```

### pandas NaN Handling
```python
# WRONG: Converts NaN to "nan" string
str(patient_info.get('Collected by', ''))

# RIGHT: Check for NaN first
if pd.isna(collected_by_value):
    ordering_provider = ''
else:
    ordering_provider = str(collected_by_value)
```

## Error Handling Philosophy

### Non-Blocking Error Strategy
```python
try:
    generate_pdf_report(...)
    summary.log_success()
except Exception as e:
    summary.log_failure(f"MR# {mrn}", f"Failed: {e}")
    # Continue processing other patients
```

**Key Principle:**
- Single entry failure doesn't stop batch
- All errors logged to RunSummary
- Enables partial success

## Main Workflow Sequence
```
1. load_and_process_data() → grouped_samples
2. For each sample:
   a. Detect duplicate Sample IDs
   b. conflict_handler() if needed
   c. generate_pdf_report()
   d. Log to RunSummary
3. generate_positives_summary_pdf()
4. generate_billing_file()
5. summary.print_summary()
```

**Critical:** Billing generation after all PDFs for complete data
