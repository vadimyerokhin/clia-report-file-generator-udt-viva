# Automated PDF Laboratory Report Generator

## Overview

This project is a Python-based application designed to automate the generation of professional laboratory reports in PDF format from a given CSV data file. It processes patient and test data, groups it by unique sample, and creates a formatted PDF report for each sample, ready for distribution.

## Features

- **CSV Data Processing**: Reads and validates input data from a CSV file using the pandas library.
- **Data Grouping**: Intelligently groups test results by unique patient sample identifiers.
- **Dynamic PDF Generation**: Creates clean, professional, and easy-to-read PDF reports using the reportlab library.
- **Filename Sanitization**: Generates safe and descriptive filenames for each report based on patient information.
- **Command-Line Interface**: Easy to use from the terminal with arguments for input and output locations.

## Requirements

- Python 3.x
- Dependencies listed in `requirements.txt` (pandas, reportlab)

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
│   └── Test_Data.csv       # Sample input data
├── src/
│   ├── main.py             # Main script, handles CLI arguments
│   ├── data_processor.py   # Handles loading and processing of CSV data
│   ├── pdf_generator.py    # Handles the creation of the PDF report
│   └── utils.py            # Utility functions (e.g., filename sanitization)
├── tests/
│   └── ...                 # Unit tests for the application
└── requirements.txt        # Project dependencies
```

## Testing

The project includes a suite of unit tests to ensure functionality and correctness. To run the tests, execute the following command from the project's root directory:

```bash
python3 -m unittest discover tests
```