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

def main(input_file, output_dir, organize_by=None):
    """Drives the PDF report generation process from start to finish.

    This function orchestrates the data processing and PDF generation. It can
    also organize the output files into subdirectories based on criteria like
    collection date, tested date, or MRN.

    Args:
        input_file (str): The full path to the input CSV file.
        output_dir (str): The path to the base directory for saving reports.
        organize_by (str, optional): The criterion for organizing reports into
            subdirectories. Accepted values: 'collection-date', 'tested-date',
            'mrn'. Defaults to None (flat structure).
    """
    summary = RunSummary()
    summary.set_output_dir(output_dir)

    # Ensure the base output directory exists
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
            error_msg = f"The date '{date_collected}' in the 'Date collected' column could not be parsed."
            summary.log_failure(f"MR# {mrn}", error_msg)
            continue

        # --- Calculate Test Completed Date ---
        try:
            latest_completion_ts = pd.to_datetime(sample_group['Test completed']).max()
            completed_date_str = latest_completion_ts.strftime('%Y-%m-%d')
            completed_date_for_pdf = latest_completion_ts.strftime('%m/%d/%Y')
        except (ValueError, TypeError) as e:
            raw_date = sample_group['Test completed'].iloc[0] if not sample_group['Test completed'].empty else "N/A"
            summary.log_error(
                f"Patient MR# {mrn}",
                f"Could not parse 'Test completed' date ('{raw_date}'). Using fallback. Error: {e}"
            )
            completed_date_str = "unknown-date"
            completed_date_for_pdf = str(raw_date).split(' ')[0]

        # --- Determine the final output directory based on organization ---
        final_output_dir = output_dir
        if organize_by:
            organize_by = organize_by.lower()
            sub_dir_name = ''
            if organize_by == 'collection-date':
                sub_dir_name = collection_date_str
            elif organize_by == 'tested-date':
                sub_dir_name = completed_date_str
            elif organize_by == 'mrn':
                sub_dir_name = f"MRN_{mrn}"

            if sub_dir_name:
                final_output_dir = os.path.join(output_dir, sub_dir_name)

        # Ensure the final output directory exists
        if not os.path.exists(final_output_dir):
            os.makedirs(final_output_dir)

        # Construct the output filename and path
        output_filename = f"{patient_name}_{mrn}_{collection_date_str}.pdf"
        output_path = os.path.join(final_output_dir, output_filename)

        selected_sample_id = sample_group['ID'].iloc[0]
        print(f"  - Generating report for {patient_info['Name']} (Sample ID: {selected_sample_id})...")

        try:
            # Step 3: Generate the PDF
            generate_pdf_report(sample_group, output_path, summary, completed_date_for_pdf)
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
    parser.add_argument(
        '--organize-by',
        choices=['collection-date', 'tested-date', 'mrn'],
        default=None,
        help="Organize PDFs into subdirectories by the specified criterion."
    )

    args = parser.parse_args()
    main(args.input, args.output, args.organize_by)