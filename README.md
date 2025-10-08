# Automated PDF Laboratory Report Generator

## Overview

This project is a Python-based application designed to automate the generation of professional laboratory reports in PDF format from a given CSV data file. It processes patient and test data, groups it by unique sample, and creates a formatted PDF report for each sample, ready for distribution.

## Features

- **CSV Data Processing**: Reads and validates input data from a CSV file using the pandas library.
- **Intelligent Data Grouping**: Groups all tests for a patient by their Medical Record Number (`MR#`) and the `Date collected` to consolidate all results from a single visit into one report.
- **Duplicate Sample Handling**: If multiple sample IDs are found for the same patient on the same day, the application prompts the user to select which sample to use, preventing ambiguity.
- **Result Filtering**: Automatically filters out and excludes any analyte results other than 'Positive' or 'Negative', printing a warning to the console for any excluded results.
- **Dynamic PDF Generation**: Creates clean, professional, and easy-to-read PDF reports using the reportlab library.
- **Filename Sanitization**: Generates safe and descriptive filenames for each report based on patient information.
- **Command-Line Interface**: Easy to use from the terminal with arguments for input and output locations.

## Requirements

- Python 3.x
- Dependencies listed in `requirements.txt` (pandas, reportlab, coverage)

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Install the required packages:**
    It is recommended to use a virtual environment to manage dependencies.
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    pip install -r requirements.txt
    ```

## Usage

The application is run from the command line, requiring a path to the input CSV file and a path to the directory where the generated PDFs should be saved.

**Command:**
```bash
python3 src/main.py -i <path_to_input_csv> -o <path_to_output_directory>
```

**Example:**
To generate reports from the sample data provided in the `data/` directory and save them to a new `output_reports/` directory, run the following command from the project root:

```bash
python3 src/main.py -i data/Test_Data.csv -o output_reports
```
The script will create the `output_reports` directory if it doesn't exist and populate it with PDF files named after each patient sample.

## Project Structure

```
.
├── data/
│   └── Test_Data.csv
├── src/
│   ├── main.py
│   ├── data_processor.py
│   ├── pdf_generator.py
│   └── utils.py
├── tests/
│   ├── test_data/
│   ├── test_data_processor.py
│   ├── test_main.py
│   ├── test_pdf_generator.py
│   ├── test_result_filtering.py
│   └── test_utils.py
└── requirements.txt
```

## Testing

The project includes a suite of unit tests to ensure functionality and correctness.

### Running Tests

To run the full test suite, execute the following command from the project's root directory:
```bash
python3 -m unittest discover tests
```

### Test Coverage

This project uses the `coverage` library to measure test coverage.

To run the tests with coverage and generate a report, use the following commands:
```bash
coverage run -m unittest discover tests
coverage report -m
```
This will print a detailed coverage report to the console, showing the coverage for each source file.