"""This module handles the loading and processing of laboratory data from CSV files.

It includes functions to read CSV data, validate necessary columns, filter for
patient-specific records, and group the data by unique patient samples for
further processing.
"""
from typing import Optional
import pandas as pd
from pandas.core.groupby.generic import DataFrameGroupBy

try:
    from src.config import REQUIRED_COLUMNS
except ImportError:
    from config import REQUIRED_COLUMNS


def load_and_process_data(
    file_path: str,
    summary: 'RunSummary'  # Forward reference to avoid circular import
) -> Optional[DataFrameGroupBy]:
    """Reads, filters, and groups patient data from a CSV file.

    This function performs the initial data ingestion and preparation. It reads a
    CSV file, validates that it contains the required columns for processing,
    filters the data to include only rows corresponding to patient samples, and
    then groups the data by the patient's medical record number and sample
    collection date. Errors are logged to the provided summary object.

    Args:
        file_path: The path to the input CSV file.
        summary: An instance of the RunSummary class for logging.

    Returns:
        A pandas DataFrameGroupBy object containing the data grouped by unique
        patient samples (by 'MR#' and 'Date collected'). Returns None if a
        critical error occurs.

    Raises:
        FileNotFoundError: If the input CSV file doesn't exist (logged to summary).
        InvalidCSVFormatError: If the CSV format is invalid (logged to summary).
        MissingColumnError: If required columns are missing (logged to summary).
    """
    # Step 1: Read the Input Data
    try:
        all_data = pd.read_csv(file_path)
        if all_data.empty:
            summary.log_error(file_path, "The file is empty.")
            return None
    except FileNotFoundError:
        summary.log_error(file_path, "The file was not found.")
        return None
    except (pd.errors.EmptyDataError, pd.errors.ParserError) as e:
        summary.log_error(file_path, f"Could not be parsed: {e}")
        return None

    # Step 2: Validate required columns
    missing_columns = [col for col in REQUIRED_COLUMNS if col not in all_data.columns]
    if missing_columns:
        summary.log_error(
            file_path,
            f"The file is missing required columns: {', '.join(missing_columns)}"
        )
        return None

    # Step 3: Filter the data to include only 'Patient' type rows
    patient_data = all_data[all_data['Type'] == 'Patient'].copy()

    if patient_data.empty:
        summary.log_error(file_path, "No data rows with Type='Patient' were found.")

    # Step 4: Group Data by Unique Patient Sample (MR# and Date collected)
    grouped_samples = patient_data.groupby(['MR#', 'Date collected'])

    return grouped_samples

if __name__ == '__main__':  # pragma: no cover
    from run_summary import RunSummary
    # This is for testing purposes to ensure the data processing works as expected.
    input_file = 'data/Test_Data.csv'
    summary = RunSummary()
    processed_data = load_and_process_data(input_file, summary)

    if processed_data:
        print(f"Successfully loaded and processed the data from {input_file}.")
        print(f"Found {len(processed_data)} unique patient samples.")
        for (mrn, date_collected), sample_group in processed_data:
            patient_name = sample_group['Name'].iloc[0]
            print(f"  - MR#: {mrn}, Date: {date_collected}, Patient: {patient_name}, Rows: {len(sample_group)}")
    summary.print_summary()