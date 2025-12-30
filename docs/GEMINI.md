# Gemini Code Assistant Context

## Project Overview

This project is a Python-based application designed to automate the generation of professional laboratory reports in PDF format from a given CSV data file. It processes patient and test data, groups it by unique sample, and creates a formatted PDF report for each sample, ready for distribution.

The application has two main entry points:
- A command-line interface (CLI) in `src/main.py`.
- A graphical user interface (GUI) in `src/gui.py`, launched by `run_gui.py`.

The core logic is in the `generate_reports` function in `src/main.py`, which is used by both the CLI and GUI.

### Key Technologies

- **Python 3.x**
- **pandas**: For data processing and manipulation.
- **reportlab**: For generating PDF reports.
- **PySide6**: For the graphical user interface.
- **unittest**: For testing.

## Building and Running

### Installation

It is recommended to use a virtual environment.

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
pip install -r requirements.txt
```

### Running the Application

**Command-Line Interface (CLI):**

```bash
python3 src/main.py -i <path_to_input_csv> -o <path_to_output_directory>
```

**Example:**

```bash
python3 src/main.py -i data/Test_Data.csv -o output_reports
```

**Graphical User Interface (GUI):**

```bash
python3 run_gui.py
```

### Running Tests

To run the full test suite:

```bash
python3 -m unittest discover tests
```

To run tests with coverage:

```bash
coverage run -m unittest discover tests
coverage report -m
```

## Development Conventions

- The project follows a standard Python project structure, with source code in `src` and tests in `tests`.
- The code is modular, with clear separation of concerns (data processing, PDF generation, GUI).
- The project uses `argparse` for command-line argument parsing.
- The GUI is built with PySide6 and uses a worker thread to keep the UI responsive during long-running tasks.
- Tests are written using the `unittest` framework and `unittest.mock`.
- The project uses a `RunSummary` class to log the results of the report generation process.
