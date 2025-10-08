import os
import argparse
import pandas as pd
from data_processor import load_and_process_data
from pdf_generator import generate_pdf_report

def main(input_file, output_dir):
    """
    Main function to drive the PDF report generation process.

    Args:
        input_file (str): Path to the input CSV file.
        output_dir (str): Directory to save the generated PDF files.
    """
    # Ensure the output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Step 1: Load and process the data
    grouped_samples = load_and_process_data(input_file)

    if not grouped_samples:
        print("No patient data found or an error occurred. Exiting.")
        return

    print(f"Found {len(grouped_samples)} unique patient samples. Generating reports...")

    # Step 2: Iterate through each sample and generate a PDF
    for (sample_id, date_collected), sample_group in grouped_samples:
        # Get patient info for filename
        patient_info = sample_group.iloc[0]
        patient_name = patient_info['Name'].replace(' ', '-')
        mrn = patient_info['MR#']

        # Format collection date for filename (YYYY-MM-DD)
        try:
            collection_date_obj = pd.to_datetime(patient_info['Date collected'])
            collection_date_str = collection_date_obj.strftime('%Y-%m-%d')
        except Exception as e:
            print(f"Warning: Could not parse date '{patient_info['Date collected']}'. Using original value. Error: {e}")
            collection_date_str = patient_info['Date collected'].replace('/', '-')

        # Construct the output filename
        output_filename = f"{patient_name}_{mrn}_{collection_date_str}.pdf"
        output_path = os.path.join(output_dir, output_filename)

        print(f"  - Generating report for {patient_info['Name']} (Sample ID: {sample_id})...")

        try:
            # Step 3: Generate the PDF
            generate_pdf_report(sample_group, output_path)
            print(f"    ...Successfully saved to {output_path}")
        except Exception as e:
            print(f"    ...Error generating PDF for sample {sample_id}: {e}")

    print("\nPDF generation process complete.")

if __name__ == '__main__':
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