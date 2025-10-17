"""This module generates medical billing files for CPT code 80307.

Medical billing file generation for presumptive drug screening tests (CPT 80307).
This module creates professional-grade CSV billing files with proper field formatting
and validation suitable for submission to medical billing systems.
"""
import csv
import os
import warnings
from datetime import datetime
from typing import Tuple
import pandas as pd


def parse_patient_name(full_name: str) -> Tuple[str, str]:
    """Parse a full name into first and last name components.

    Handles various name formats common in medical records:
    - Standard "FIRST LAST" format
    - Multiple word last names "FIRST MIDDLE LAST"
    - Single names
    - Empty/invalid names

    Args:
        full_name (str): The full patient name (typically "FIRSTNAME LASTNAME").

    Returns:
        tuple[str, str]: A tuple containing (first_name, last_name).
            - For "JOHN SMITH": returns ("JOHN", "SMITH")
            - For "MARY ANN SMITH": returns ("MARY", "ANN SMITH")
            - For "CHER": returns ("", "CHER")
            - For empty/None: returns ("", "UNKNOWN")
    """
    if not full_name or pd.isna(full_name):
        return ("", "UNKNOWN")

    # Clean up the name: strip whitespace and handle multiple spaces
    name = str(full_name).strip()
    if not name:
        return ("", "UNKNOWN")

    # Split on whitespace
    parts = name.split()

    if len(parts) == 0:
        return ("", "UNKNOWN")
    elif len(parts) == 1:
        # Single name - use as last name
        return ("", parts[0])
    else:
        # Multiple parts - first word is first name, rest is last name
        first_name = parts[0]
        last_name = " ".join(parts[1:])
        return (first_name, last_name)


def format_date_for_billing(date_value, default: str = "UNKNOWN") -> str:
    """Format a date value to MM/DD/YYYY format for medical billing.

    This function handles various input date formats and converts them to the
    standard US medical billing date format (MM/DD/YYYY). It uses pandas
    datetime parsing to handle multiple input formats gracefully.

    Args:
        date_value: The date value to format. Can be a string, datetime,
            or pandas Timestamp.
        default (str): The value to return if date parsing fails.
            Defaults to "UNKNOWN".

    Returns:
        str: The formatted date as MM/DD/YYYY, or the default value if
            parsing fails.

    Examples:
        >>> format_date_for_billing("10/2/2025")
        '10/02/2025'
        >>> format_date_for_billing("2025-10-02")
        '10/02/2025'
        >>> format_date_for_billing(None)
        'UNKNOWN'
    """
    if pd.isna(date_value) or not date_value:
        return default

    try:
        # Try to parse the date using pandas
        dt = pd.to_datetime(date_value)
        # Format as MM/DD/YYYY
        return dt.strftime('%m/%d/%Y')
    except (ValueError, TypeError, AttributeError):
        return default


def generate_billing_file(grouped_samples, output_dir: str, summary) -> str:
    """Generate a CPT code 80307 billing file from processed patient samples.

    Creates a professional CSV file containing billing records for each unique
    patient sample. Each record represents one billable CPT 80307 service
    (presumptive drug screening). The file is formatted for direct use by
    medical billing systems.

    Args:
        grouped_samples: A pandas DataFrameGroupBy object containing patient
            samples grouped by (MR#, Date collected).
        output_dir (str): The directory where the billing file should be saved.
        summary: A RunSummary instance for logging billing generation status.

    Returns:
        str: The full path to the generated billing file.

    Raises:
        Exception: If file generation fails (logged to summary, not raised).

    File Format:
        - CSV with headers
        - UTF-8 encoding for compatibility
        - One row per billable service
        - Filename: billing_80307_YYYYMMDD_HHMMSS.csv
    """
    # Generate timestamp for unique filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    billing_filename = f"billing_80307_{timestamp}.csv"
    billing_filepath = os.path.join(output_dir, billing_filename)

    # Define billing file columns
    fieldnames = [
        'Patient_Last_Name',
        'Patient_First_Name',
        'Patient_MRN',
        'Date_of_Birth',
        'Date_of_Service',
        'CPT_Code',
        'Units',
        'Specimen_ID',
        'Ordering_Provider',
        'Test_Completed_Date'
    ]

    billing_records = []
    skipped_count = 0

    # Process each patient sample group
    for (mrn, date_collected), patient_group in grouped_samples:
        patient_info = patient_group.iloc[0]

        # Parse patient name
        first_name, last_name = parse_patient_name(patient_info.get('Name', ''))

        # Validate critical fields
        if not mrn or pd.isna(mrn):
            summary.log_billing_failure(
                "UNKNOWN",
                "Missing MRN - cannot create billing entry"
            )
            skipped_count += 1
            continue

        # Format dates
        date_of_service = format_date_for_billing(date_collected)
        date_of_birth = format_date_for_billing(
            patient_info.get('Date of Birth', ''),
            default=""
        )

        # Get test completed date
        try:
            # Suppress pandas datetime parsing warnings
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', category=UserWarning, message='Could not infer format')
                latest_completion = pd.to_datetime(patient_group['Test completed'], errors='coerce').max()
            if pd.notna(latest_completion):
                test_completed_date = latest_completion.strftime('%m/%d/%Y')
            else:
                test_completed_date = ""
        except (ValueError, TypeError, KeyError):
            test_completed_date = ""

        # Get specimen ID (handle multiple IDs by using first one)
        specimen_id = str(patient_info.get('ID', ''))

        # Get ordering provider (Collected by field)
        collected_by_value = patient_info.get('Collected by', '')
        if pd.isna(collected_by_value) or collected_by_value == '':
            ordering_provider = ''
        else:
            ordering_provider = str(collected_by_value)

        # Create billing record
        billing_record = {
            'Patient_Last_Name': last_name,
            'Patient_First_Name': first_name,
            'Patient_MRN': str(mrn),
            'Date_of_Birth': date_of_birth,
            'Date_of_Service': date_of_service,
            'CPT_Code': '80307',
            'Units': '1',
            'Specimen_ID': specimen_id,
            'Ordering_Provider': ordering_provider,
            'Test_Completed_Date': test_completed_date
        }

        billing_records.append(billing_record)
        summary.log_billing_success()

    # Write billing records to CSV file
    try:
        with open(billing_filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(billing_records)

        summary.set_billing_file_path(billing_filepath)

        return billing_filepath

    except Exception as e:
        summary.log_billing_failure(
            "FILE_WRITE",
            f"Failed to write billing file: {e}"
        )
        raise


if __name__ == '__main__':  # pragma: no cover
    # Test module functionality
    from data_processor import load_and_process_data
    from run_summary import RunSummary

    print("Testing billing file generation...")

    summary = RunSummary()
    input_file = 'data/Test_Data.csv'
    grouped_samples = load_and_process_data(input_file, summary)

    if grouped_samples:
        output_dir = 'output_billing_test'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        billing_file = generate_billing_file(grouped_samples, output_dir, summary)
        print(f"✓ Billing file generated: {billing_file}")

        # Display sample records
        import pandas as pd
        df = pd.read_csv(billing_file)
        print(f"\n✓ Total billing entries: {len(df)}")
        print("\nSample billing records:")
        print(df.head().to_string(index=False))
    else:
        print("✗ Failed to load sample data")
