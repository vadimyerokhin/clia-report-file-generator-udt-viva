"""This module handles the loading and processing of laboratory data from CSV files.

It includes functions to read CSV data, validate necessary columns, filter for
patient-specific records, and group the data by unique patient samples for
further processing.
"""
import pandas as pd

def load_and_process_data(file_path):
    """Reads, filters, and groups patient data from a CSV file.

    This function performs the initial data ingestion and preparation. It reads a
    CSV file, validates that it contains the required columns for processing,
    filters the data to include only rows corresponding to patient samples, and
    then groups the data by the patient's medical record number and sample
    collection date. Error handling is included for missing files, empty files,
    or parsing errors.

    Args:
        file_path (str): The path to the input CSV file.

    Returns:
        pandas.core.groupby.generic.DataFrameGroupBy: A pandas DataFrameGroupBy
        object containing the data grouped by unique patient samples (by 'MR#'
        and 'Date collected'). Returns None if the file is not found, is empty,
        is missing required columns, or a parsing error occurs.
    """
    # Step 1: Read the Input Data
    try:
        all_data = pd.read_csv(file_path)
        if all_data.empty:
            print(f"Warning: The file at {file_path} is empty.")
            return None
    except FileNotFoundError:
        print(f"Error: The file at {file_path} was not found.")
        return None
    except (pd.errors.EmptyDataError, pd.errors.ParserError) as e:
        print(f"Error parsing CSV file {file_path}: {e}")
        return None

    # Step 2: Validate required columns
    required_columns = [
        'Type', 'ID', 'Date collected', 'Name', 'MR#', 'Date of Birth',
        'Collected by', 'Test completed', 'Test Name', 'Test result'
    ]
    missing_columns = [col for col in required_columns if col not in all_data.columns]
    if missing_columns:
        print(f"Error: The file {file_path} is missing the following required columns: {', '.join(missing_columns)}")
        return None

    # Step 3: Filter the data to include only 'Patient' type rows
    patient_data = all_data[all_data['Type'] == 'Patient'].copy()

    if patient_data.empty:
        print(f"Warning: No 'Patient' data found in {file_path}.")

    # Step 4: Group Data by Unique Patient Sample (MR# and Date collected)
    grouped_samples = patient_data.groupby(['MR#', 'Date collected'])

    return grouped_samples

if __name__ == '__main__':  # pragma: no cover
    # This is for testing purposes to ensure the data processing works as expected.
    input_file = 'data/Test_Data.csv'
    processed_data = load_and_process_data(input_file)

    if processed_data:
        print(f"Successfully loaded and processed the data from {input_file}.")
        print(f"Found {len(processed_data)} unique patient samples.")
        for (sample_id, date_collected), sample_group in processed_data:
            patient_name = sample_group['Name'].iloc[0]
            print(f"  - Sample ID: {sample_id}, Date: {date_collected}, Patient: {patient_name}, Rows: {len(sample_group)}")