"""This module serves as the main entry point for the application.

It handles command-line argument parsing and orchestrates the entire process
of reading data, processing it, and generating PDF reports. The main function
drives the workflow from data input to report output.
"""
import os
import argparse
import pandas as pd
from data_processor import load_and_process_data
from pdf_generator import generate_pdf_report
from utils import sanitize_filename
from run_summary import RunSummary

def main(input_file, output_dir):
    """Drives the PDF report generation process from start to finish.

    This function takes a path to an input CSV file and an output directory.
    It reads the data, processes and groups it by patient sample, and then
    iterates through each group to generate a formatted PDF report, which is
    saved in the specified output directory.

    Args:
        input_file (str): The full path to the input CSV file containing the
            laboratory test data.
        output_dir (str): The path to the directory where the generated PDF
            report files will be saved. The directory will be created if it
            does not exist.
    """
    summary = RunSummary()
    summary.set_output_dir(output_dir)

    # Ensure the output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Step 1: Load and process the data
    grouped_samples = load_and_process_data(input_file, summary)

    if not grouped_samples:
        summary.print_summary()
        return

    summary.set_total_samples(len(grouped_samples))
    print(f"Found {len(grouped_samples)} unique patient groups. Generating reports...")

    # Step 2: Iterate through each patient group and generate a PDF
    for (mrn, date_collected), patient_group in grouped_samples:
        sample_group = patient_group
        unique_sample_ids = patient_group['ID'].unique()

        # If multiple samples exist for the same patient on the same day, prompt user
        if len(unique_sample_ids) > 1:
            print(f"\nConflict: Multiple sample records found for patient MR# {mrn} on {date_collected}.")
            print("Please select which sample to generate a report for:")
            for i, sample_id in enumerate(unique_sample_ids):
                print(f"  {i + 1}: Sample ID {sample_id}")

            # Get user's choice
            while True:
                try:
                    choice = input(f"Enter your choice (1-{len(unique_sample_ids)}, or 's' to skip): ")
                    if choice.lower() == 's':
                        print("\nOperation cancelled by user. Skipping this patient.")
                        # Find a representative sample ID to log the skip
                        skipped_id = unique_sample_ids[0]
                        summary.log_user_skip(mrn, date_collected, skipped_id)
                        sample_group = None
                        break

                    choice_idx = int(choice) - 1
                    if 0 <= choice_idx < len(unique_sample_ids):
                        selected_id = unique_sample_ids[choice_idx]
                        sample_group = patient_group[patient_group['ID'] == selected_id].copy()
                        print(f"  > Processing selected Sample ID: {selected_id}")
                        break
                    else:
                        print(f"  > Invalid choice. Please enter a number between 1 and {len(unique_sample_ids)}.")
                except ValueError:
                    print("  > Invalid input. Please enter a number or 's'.")
                except (KeyboardInterrupt, EOFError):
                    skipped_id = unique_sample_ids[0]
                    summary.log_user_skip(mrn, date_collected, skipped_id)
                    sample_group = None  # Skip processing
                    break

        if sample_group is None or sample_group.empty:
            continue

        # Get patient info for filename
        patient_info = sample_group.iloc[0]
        patient_name = sanitize_filename(patient_info['Name'])
        # mrn is from the groupby key

        # Format collection date for filename (YYYY-MM-DD)
        try:
            collection_date_obj = pd.to_datetime(date_collected)
            collection_date_str = collection_date_obj.strftime('%Y-%m-%d')
        except Exception:
            # Log a failure and skip this group
            error_msg = f"The date '{date_collected}' in the 'Date collected' column could not be parsed."
            summary.log_failure(f"MR# {mrn}", error_msg)
            continue

        # Construct the output filename
        output_filename = f"{patient_name}_{mrn}_{collection_date_str}.pdf"
        output_path = os.path.join(output_dir, output_filename)

        selected_sample_id = sample_group['ID'].iloc[0]
        print(f"  - Generating report for {patient_info['Name']} (Sample ID: {selected_sample_id})...")

        try:
            # Step 3: Generate the PDF
            generate_pdf_report(sample_group, output_path, summary)
            summary.log_success()
            print(f"    ...Successfully saved to {output_path}")
        except Exception as e:
            summary.log_failure(f"MR# {mrn} / Sample {selected_sample_id}", f"Failed to generate PDF: {e}")
            print(f"    ...Error generating PDF for sample {selected_sample_id}")

    summary.print_summary()

if __name__ == '__main__':  # pragma: no cover
    parser = argparse.ArgumentParser(description="Automated PDF Laboratory Report Generator")
    parser.add_argument(
        '-i', '--input',
        required=True,
        help="Path to the input CSV file."
    )
    parser.add_argument(
        '-o', '--output',
        required=True,
        help="Directory to save the generated PDF reports."
    )

    args = parser.parse_args()
    main(args.input, args.output)