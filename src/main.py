"""This module serves as the main entry point for the application.

It handles command-line argument parsing and orchestrates the entire process
of reading data, processing it, and generating PDF reports. The main function
drives the workflow from data input to report output.
"""
import os
import argparse
import pandas as pd
from data_processor import load_and_process_data
from pdf_generator import generate_pdf_report, generate_positives_summary_pdf
from billing_generator import generate_billing_file
from utils import sanitize_filename
from run_summary import RunSummary

def generate_reports(input_file, output_dir, organize_by, summary, progress_callback=None, conflict_handler=None):
    """
    Generates PDF reports based on the provided parameters. This function contains the core logic.
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

        try:
            collection_date_obj = pd.to_datetime(date_collected)
            collection_date_str = collection_date_obj.strftime('%Y-%m-%d')
        except Exception:
            error_msg = f"The date '{date_collected}' in the 'Date collected' column could not be parsed."
            summary.log_failure(f"MR# {mrn}", error_msg)
            continue

        try:
            latest_completion_ts = pd.to_datetime(sample_group['Test completed']).max()
            completed_date_str = latest_completion_ts.strftime('%Y-%m-%d')
            completed_date_for_pdf = latest_completion_ts.strftime('%m/%d/%Y')
        except (ValueError, TypeError) as e:
            raw_date = sample_group['Test completed'].iloc[0] if not sample_group['Test completed'].empty else "N/A"
            summary.log_error(f"Patient MR# {mrn}", f"Could not parse 'Test completed' date ('{raw_date}'). Error: {e}")
            completed_date_str = "unknown-date"
            completed_date_for_pdf = str(raw_date).split(' ')[0]

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

    # Generate billing file after all PDFs are processed
    if progress_callback:
        progress_callback("\nGenerating medical billing file (CPT 80307)...")

    try:
        billing_file_path = generate_billing_file(grouped_samples, output_dir, summary)
        if progress_callback:
            progress_callback(f"Successfully generated billing file: {billing_file_path}")
    except Exception as e:
        if progress_callback:
            progress_callback(f"Error generating billing file: {e}")
        summary.log_error("Billing File", f"Failed to generate billing file: {e}")

def main(input_file, output_dir, organize_by=None):
    """Drives the PDF report generation process from start to finish for the CLI."""
    summary = RunSummary()

    def cli_conflict_handler(mrn, date_collected, unique_sample_ids):
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

    generate_reports(input_file, output_dir, organize_by, summary, progress_callback=print, conflict_handler=cli_conflict_handler)

    # Generate the summary PDF of positive results
    try:
        generate_positives_summary_pdf(summary, output_dir)
        if summary._positive_results:
            print(f"Successfully generated positives summary PDF: {os.path.join(output_dir, 'positives_summary.pdf')}")
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