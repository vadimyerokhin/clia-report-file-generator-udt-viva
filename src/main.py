"""This module serves as the main entry point for the application.

It handles command-line argument parsing and orchestrates the entire process
of reading data, processing it, and generating PDF reports. The main function
drives the workflow from data input to report output.
"""
import os
import argparse
from typing import Optional, Callable
import pandas as pd

try:
    from src.data_processor import load_and_process_data
    from src.pdf_generator import generate_pdf_report, generate_positives_summary_pdf
    from src.utils import sanitize_filename, parse_collection_date, parse_completion_date
    from src.run_summary import RunSummary
    from src.config import POSITIVES_SUMMARY_FILENAME
except ImportError:
    from data_processor import load_and_process_data
    from pdf_generator import generate_pdf_report, generate_positives_summary_pdf
    from utils import sanitize_filename, parse_collection_date, parse_completion_date
    from run_summary import RunSummary
    from config import POSITIVES_SUMMARY_FILENAME


def cli_conflict_handler(mrn, date_collected, unique_sample_ids):
    """Handles sample ID conflicts in CLI mode by prompting the user.

    Args:
        mrn: The medical record number.
        date_collected: The collection date.
        unique_sample_ids: List of conflicting sample IDs.

    Returns:
        The index of the selected sample, or None if skipped.
    """
    print(f"\nConflict: Multiple sample records found for patient MR# {mrn} on {date_collected}.")
    print("Please select which sample to generate a report for:")
    for i, sample_id in enumerate(unique_sample_ids):
        print(f"  {i + 1}: Sample ID {sample_id}")

    while True:
        try:
            choice = input(f"Enter your choice (1-{len(unique_sample_ids)}, or 's' to skip): ")
            if choice.lower() == 's':
                return None
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(unique_sample_ids):
                return choice_idx
            else:
                print(f"  > Invalid choice. Please enter a number between 1 and {len(unique_sample_ids)}.")
        except ValueError:
            print("  > Invalid input. Please enter a number or 's'.")
        except (EOFError, KeyboardInterrupt):
            print("\nOperation cancelled by user.")
            return None

def generate_reports(
    input_file: str,
    output_dir: str,
    organize_by: Optional[str],
    summary: RunSummary,
    progress_callback: Optional[Callable[[str], None]] = None,
    conflict_handler: Optional[Callable[[str, str, list], Optional[int]]] = None
) -> None:
    """Generates PDF reports based on the provided parameters.

    This function contains the core logic for processing CSV data and generating
    individual PDF reports for each patient sample.

    Args:
        input_file: Path to the input CSV file.
        output_dir: Directory to save the generated PDF reports.
        organize_by: Method to organize output files ('collection-date', 'tested-date', 'mrn', or None).
        summary: RunSummary instance for tracking execution statistics.
        progress_callback: Optional callback function for progress updates.
        conflict_handler: Optional callback for handling duplicate sample IDs.
    """
    summary.set_output_dir(output_dir)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    grouped_samples = load_and_process_data(input_file, summary)

    if not grouped_samples:
        if progress_callback:
            progress_callback("No valid data found to process.")
        return

    summary.set_total_samples(len(grouped_samples))
    if progress_callback:
        progress_callback(f"Found {len(grouped_samples)} unique patient groups. Generating reports...")

    for (mrn, date_collected), patient_group in grouped_samples:
        sample_group = patient_group
        unique_sample_ids = patient_group['ID'].unique()

        if len(unique_sample_ids) > 1:
            if conflict_handler:
                selected_index = conflict_handler(mrn, date_collected, unique_sample_ids)
                if selected_index is not None and 0 <= selected_index < len(unique_sample_ids):
                    selected_id = unique_sample_ids[selected_index]
                    sample_group = patient_group[patient_group['ID'] == selected_id].copy()
                    if progress_callback:
                        progress_callback(f"  > Processing selected Sample ID: {selected_id}")
                else:
                    skipped_id = unique_sample_ids[0]
                    summary.log_user_skip(mrn, date_collected, skipped_id)
                    if progress_callback:
                        progress_callback(f"Skipping patient MR# {mrn} on {date_collected} due to user cancellation.")
                    continue
            else: # Fallback to command-line prompt if no handler
                # ... (existing input logic)
                pass

        if sample_group is None or sample_group.empty:
            continue

        patient_info = sample_group.iloc[0]
        patient_name = sanitize_filename(patient_info['Name'])

        # Parse collection date
        collection_date_str, collection_error = parse_collection_date(date_collected)
        if collection_error:
            summary.log_failure(f"MR# {mrn}", collection_error)
            continue

        # Parse completion date
        completed_date_str, completed_date_for_pdf, completion_error = parse_completion_date(
            sample_group['Test completed']
        )
        if completion_error:
            summary.log_error(f"Patient MR# {mrn}", completion_error)

        final_output_dir = output_dir
        if organize_by:
            sub_dir_name = ''
            if organize_by == 'collection-date':
                sub_dir_name = collection_date_str
            elif organize_by == 'tested-date':
                sub_dir_name = completed_date_str
            elif organize_by == 'mrn':
                sub_dir_name = f"MRN_{mrn}"
            if sub_dir_name:
                final_output_dir = os.path.join(output_dir, sub_dir_name)

        if not os.path.exists(final_output_dir):
            os.makedirs(final_output_dir)

        output_filename = f"{patient_name}_{mrn}_{collection_date_str}.pdf"
        output_path = os.path.join(final_output_dir, output_filename)
        selected_sample_id = sample_group['ID'].iloc[0]

        if progress_callback:
            progress_callback(f"  - Generating report for {patient_info['Name']} (Sample ID: {selected_sample_id})...")

        try:
            generate_pdf_report(sample_group, output_path, summary, completed_date_for_pdf, input_file)
            summary.log_success()
            if progress_callback:
                progress_callback(f"    ...Successfully saved to {output_path}")
        except Exception as e:
            summary.log_failure(f"MR# {mrn} / Sample {selected_sample_id}", f"Failed to generate PDF: {e}")
            if progress_callback:
                progress_callback(f"    ...Error generating PDF for sample {selected_sample_id}")

def main(input_file: str, output_dir: str, organize_by: Optional[str] = None) -> None:
    """Drives the PDF report generation process from start to finish for the CLI.

    Args:
        input_file: Path to the input CSV file.
        output_dir: Directory to save the generated PDF reports.
        organize_by: Optional method to organize output files.
    """
    summary = RunSummary()

    generate_reports(input_file, output_dir, organize_by, summary, progress_callback=print, conflict_handler=cli_conflict_handler)

    # Generate the summary PDF of positive results
    try:
        generate_positives_summary_pdf(summary, output_dir)
        if summary.positive_results:
            summary_path = os.path.join(output_dir, POSITIVES_SUMMARY_FILENAME)
            print(f"Successfully generated positives summary PDF: {summary_path}")
    except Exception as e:
        print(f"Error generating positives summary PDF: {e}")

    summary.print_summary()

if __name__ == '__main__':  # pragma: no cover
    parser = argparse.ArgumentParser(description="Automated PDF Laboratory Report Generator")
    parser.add_argument('-i', '--input', required=True, help="Path to the input CSV file.")
    parser.add_argument('-o', '--output', required=True, help="Directory to save the generated PDF reports.")
    parser.add_argument('--organize-by', choices=['collection-date', 'tested-date', 'mrn'], default=None, help="Organize PDFs into subdirectories.")

    args = parser.parse_args()
    main(args.input, args.output, args.organize_by)