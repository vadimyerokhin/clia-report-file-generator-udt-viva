"""This module is responsible for generating PDF reports from processed data.

It uses the reportlab library to construct a PDF document containing a laboratory
report for a single patient sample. The module defines functions to create
various components of the report, such as headers, footers, patient information
tables, and test result tables.
"""
import os
from typing import Any
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.colors import black, lightgrey
from reportlab.lib.units import inch

try:
    from src.config import (
        LAB_NAME, LAB_CLIA_ID, LAB_ADDRESS, LAB_CITY_STATE_ZIP,
        LAB_PHONE, LAB_EMAIL, LAB_DIRECTOR, REPORT_TITLE,
        SPECIMEN_TYPE, VALID_RESULTS, PDF_MARGIN, PDF_SPACER_SMALL,
        PDF_SPACER_MEDIUM, PDF_SPACER_LARGE, POSITIVES_SUMMARY_FILENAME,
        PDF_PATIENT_TABLE_COL_WIDTH, PDF_SPECIMEN_LABEL_WIDTH,
        PDF_SPECIMEN_VALUE_WIDTH, PDF_RESULTS_TEST_NAME_WIDTH,
        PDF_RESULTS_RESULT_WIDTH, PDF_RESULTS_UNITS_WIDTH,
        PDF_RESULTS_FLAGS_WIDTH, PDF_RESULTS_COMMENTS_WIDTH,
        PDF_HEADER_LINE_WIDTH, PDF_POSITIVES_NAME_WIDTH,
        PDF_POSITIVES_MRN_WIDTH, PDF_POSITIVES_DATE_WIDTH,
        PDF_POSITIVES_TEST_WIDTH
    )
except ImportError:
    from config import (
        LAB_NAME, LAB_CLIA_ID, LAB_ADDRESS, LAB_CITY_STATE_ZIP,
        LAB_PHONE, LAB_EMAIL, LAB_DIRECTOR, REPORT_TITLE,
        SPECIMEN_TYPE, VALID_RESULTS, PDF_MARGIN, PDF_SPACER_SMALL,
        PDF_SPACER_MEDIUM, PDF_SPACER_LARGE, POSITIVES_SUMMARY_FILENAME,
        PDF_PATIENT_TABLE_COL_WIDTH, PDF_SPECIMEN_LABEL_WIDTH,
        PDF_SPECIMEN_VALUE_WIDTH, PDF_RESULTS_TEST_NAME_WIDTH,
        PDF_RESULTS_RESULT_WIDTH, PDF_RESULTS_UNITS_WIDTH,
        PDF_RESULTS_FLAGS_WIDTH, PDF_RESULTS_COMMENTS_WIDTH,
        PDF_HEADER_LINE_WIDTH, PDF_POSITIVES_NAME_WIDTH,
        PDF_POSITIVES_MRN_WIDTH, PDF_POSITIVES_DATE_WIDTH,
        PDF_POSITIVES_TEST_WIDTH
    )


def safe_str(value: Any) -> str:
    """Safely converts a value to string, handling None and NaN values.

    This utility function eliminates the repeated pd.notna() pattern throughout the code.

    Args:
        value: The value to convert to string.

    Returns:
        The string representation of the value, or empty string if None/NaN.
    """
    return str(value) if pd.notna(value) else ''


class PDFStyleFactory:
    """Factory class for creating consistent PDF paragraph styles.

    This class eliminates the duplication of ParagraphStyle creation
    throughout the module by providing reusable style creation methods.
    """

    def __init__(self):
        """Initializes the style factory with base styles."""
        self.base_styles = getSampleStyleSheet()

    def create_header_style(self) -> ParagraphStyle:
        """Creates the main header style for the laboratory header."""
        return ParagraphStyle(
            'header_style',
            parent=self.base_styles['Normal'],
            fontSize=8,
            alignment=TA_LEFT
        )

    def create_title_style(self) -> ParagraphStyle:
        """Creates the title style for report title."""
        return ParagraphStyle(
            'title_style',
            parent=self.base_styles['h1'],
            fontSize=14,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )

    def create_info_header_style(self) -> ParagraphStyle:
        """Creates the style for section headers (Patient/Specimen Information)."""
        return ParagraphStyle(
            'info_header',
            parent=self.base_styles['h2'],
            fontName='Helvetica-Bold',
            fontSize=12,
            alignment=TA_LEFT
        )

    def create_patient_style(self) -> ParagraphStyle:
        """Creates the base style for patient information text."""
        return ParagraphStyle(
            'patient_style',
            parent=self.base_styles['Normal'],
            fontName='Helvetica',
            fontSize=10
        )

    def create_patient_bold_style(self) -> ParagraphStyle:
        """Creates the bold style for patient information labels."""
        base = self.create_patient_style()
        return ParagraphStyle(
            'patient_bold_style',
            parent=base,
            fontName='Helvetica-Bold'
        )

    def create_note_style(self) -> ParagraphStyle:
        """Creates the style for the positive results note."""
        return ParagraphStyle(
            'note_style',
            parent=self.base_styles['Normal'],
            fontName='Helvetica-Oblique',
            fontSize=10
        )

    def create_table_header_style(self) -> ParagraphStyle:
        """Creates the style for table headers."""
        return ParagraphStyle(
            'table_header',
            parent=self.base_styles['h2'],
            fontName='Helvetica-Bold',
            fontSize=12,
            alignment=TA_LEFT
        )

    def create_footer_header_style(self) -> ParagraphStyle:
        """Creates the style for footer section header."""
        return ParagraphStyle(
            'footer_header',
            parent=self.base_styles['h2'],
            fontName='Helvetica-Bold',
            fontSize=12,
            alignment=TA_LEFT
        )

    def create_footer_text_style(self) -> ParagraphStyle:
        """Creates the style for footer body text."""
        return ParagraphStyle(
            'footer_text',
            parent=self.base_styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=12
        )

    def create_intro_style(self) -> ParagraphStyle:
        """Creates the style for introduction text in summary reports."""
        return ParagraphStyle(
            'intro_style',
            parent=self.base_styles['Normal'],
            alignment=TA_LEFT
        )

def generate_pdf_report(sample_group, output_filename, summary, completed_date, input_filename=""):
    """Generates and saves a complete PDF report for a single patient sample.

    This function orchestrates the creation of a PDF document by assembling
    various components (header, title, info tables, results, footer). It takes a
    DataFrame group corresponding to a single sample, filters out invalid test
    results, and saves the generated PDF to the specified file.

    Args:
        sample_group (pd.DataFrame): A DataFrame containing all data rows for a
            single, unique patient sample.
        output_filename (str): The path (including filename) where the
            generated PDF report will be saved.
        summary (RunSummary): An instance of the RunSummary class for logging.
        completed_date (str): The pre-formatted 'Test Completed Date' for the
            report.
        input_filename (str): The name of the input CSV file.
    """
    doc = SimpleDocTemplate(output_filename, pagesize=letter,
                            rightMargin=inch, leftMargin=inch,
                            topMargin=inch, bottomMargin=inch)
    story = []

    # Get consistent patient info from the first row of the group
    patient_info = sample_group.iloc[0]
    mrn = patient_info['MR#']

    # --- Filter out invalid results ---
    # Ensure 'Test result' column is string type to use .str accessor
    sample_group['Test result'] = sample_group['Test result'].astype(str)
    valid_mask = sample_group['Test result'].str.strip().str.lower().isin(VALID_RESULTS)

    valid_results_df = sample_group[valid_mask]
    invalid_results_df = sample_group[~valid_mask]

    # Log any invalid results to the summary
    for _, row in invalid_results_df.iterrows():
        summary.log_invalid_result(mrn, row['Test Name'], row['Test result'])

    # --- 1. Laboratory Header ---
    story.extend(get_lab_header())
    story.append(Spacer(1, PDF_SPACER_MEDIUM * inch))

    # --- 2. Report Title ---
    story.append(get_report_title())
    story.append(Spacer(1, PDF_SPACER_MEDIUM * inch))

    # --- 3. Patient and Specimen Info ---
    story.extend(get_info_tables(patient_info, summary, completed_date, input_filename))
    story.append(Spacer(1, PDF_SPACER_MEDIUM * inch))

    # --- 4. Conditional Positive Note & Log Positives ---
    positive_mask = valid_results_df['Test result'].str.strip().str.lower() == 'positive'
    positive_results = valid_results_df[positive_mask]

    if not positive_results.empty:
        story.append(get_conditional_note())
        story.append(Spacer(1, PDF_SPACER_SMALL * inch))
        # Log each positive result for the summary report
        for _, row in positive_results.iterrows():
            summary.log_positive_result(
                mrn=mrn,
                patient_name=patient_info['Name'],
                test_name=row['Test Name'],
                collection_date=patient_info['Date collected']
            )

    # --- 5. Test Results Table ---
    # Generate the table using ONLY the valid results, if any exist
    if not valid_results_df.empty:
        story.extend(get_results_table(valid_results_df))

    # --- 6. Footer ---
    story.append(Spacer(1, PDF_SPACER_LARGE * inch))
    story.extend(get_footer())

    doc.build(story)


def get_footer():
    """Creates and returns the footer section of the report.

    The footer contains information regarding the interpretation of test results,
    including definitions for 'Negative' and 'Positive' results, and a
    disclaimer note.

    Returns:
        list: A list of ReportLab Flowables representing the formatted footer.
    """
    style_factory = PDFStyleFactory()
    footer_header_style = style_factory.create_footer_header_style()
    footer_text_style = style_factory.create_footer_text_style()

    footer_header = Paragraph("interpretation of results", footer_header_style)

    p1_text = "<b>Negative :</b> The absence of the drug/drug metabolite in the sample at or above the cut-off concentration of the assay."
    p2_text = "<b>Positive :</b> The presence of drug/drug metabolite in the sample at or above the cut-off concentration of the assay."
    p3_text = "<b>Note :</b> The results of this test are to be used for clinical purposes only. This is a presumptive test. It is recommended that a more specific confirmatory test be used to confirm a positive result."

    p1 = Paragraph(p1_text, footer_text_style)
    p2 = Paragraph(p2_text, footer_text_style)
    p3 = Paragraph(p3_text, footer_text_style)

    return [
        footer_header,
        Spacer(1, PDF_SPACER_SMALL*inch), p1,
        Spacer(1, PDF_SPACER_SMALL*inch), p2,
        Spacer(1, PDF_SPACER_SMALL*inch), p3
    ]


def get_lab_header() -> list[Any]:
    """Creates and returns the main header for the laboratory report.

    The header includes the laboratory's name, CLIA ID, address, contact
    information, and the name of the laboratory director, followed by a
    horizontal line.

    Returns:
        A list of ReportLab Flowables representing the formatted header.
    """
    style_factory = PDFStyleFactory()
    header_text = (
        f"{LAB_NAME} | CLIA ID: {LAB_CLIA_ID} | {LAB_ADDRESS} | {LAB_CITY_STATE_ZIP} | "
        f"p. {LAB_PHONE} | e. {LAB_EMAIL} | Laboratory Director: {LAB_DIRECTOR}"
    )
    header_style = style_factory.create_header_style()
    header = Paragraph(header_text, header_style)
    # The horizontal line will be drawn directly on the canvas in a more advanced setup.
    # For SimpleDocTemplate, we can simulate it with a table.
    line = Table(
        [['']],
        colWidths=[PDF_HEADER_LINE_WIDTH * inch],
        style=TableStyle([('LINEBELOW', (0,0), (-1,-1), 1, black)])
    )
    return [header, line]


def get_report_title() -> Paragraph:
    """Creates and returns the main title of the report.

    Returns:
        A styled paragraph object for the title.
    """
    style_factory = PDFStyleFactory()
    title_style = style_factory.create_title_style()
    title = Paragraph(REPORT_TITLE, title_style)
    return title

def get_info_tables(patient_info, summary, completed_date, input_filename=""):
    """Creates the patient and specimen information tables.

    This function constructs two formatted tables: one for patient demographics
    (Name, DOB, MRN) and one for specimen details (Type, ID, Collection Date,
    etc.).

    Args:
        patient_info (pd.Series): A pandas Series containing the demographic
            information for the patient. It's expected to be the first row
            of the sample group.
        summary (RunSummary): An instance of the RunSummary class for logging.
        completed_date (str): The pre-formatted 'Test Completed Date' to be
            displayed in the specimen information table.
        input_filename (str, optional): The name of the source CSV file.
            Defaults to "".

    Returns:
        list: A list of ReportLab Flowables, including headers and tables for
            patient and specimen information.
    """
    style_factory = PDFStyleFactory()
    patient_style = style_factory.create_patient_style()
    patient_bold_style = style_factory.create_patient_bold_style()
    info_header_style = style_factory.create_info_header_style()

    # --- Patient Information Block ---
    patient_header = Paragraph("Patient Information", info_header_style)

    # Safely get patient info, converting None or NaN to empty strings
    name = safe_str(patient_info['Name'])
    dob = safe_str(patient_info['Date of Birth'])
    mrn = safe_str(patient_info['MR#'])

    patient_data = [
        [Paragraph("Patient Name", patient_bold_style), Paragraph("DOB", patient_bold_style), Paragraph("Patient id", patient_bold_style)],
        [Paragraph(name, patient_style), Paragraph(dob, patient_style), Paragraph(mrn, patient_style)]
    ]
    patient_table = Table(
        patient_data,
        colWidths=[PDF_PATIENT_TABLE_COL_WIDTH * inch] * 3
    )
    patient_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
    ]))

    # --- Specimen Information Block ---
    specimen_header = Paragraph("Specimen Information", info_header_style)

    # Safely get specimen info, converting None or NaN to empty strings
    specimen_id = safe_str(patient_info['ID'])
    collection_date = safe_str(patient_info['Date collected'])
    collected_by = safe_str(patient_info['Collected by'])

    # Combine Specimen ID with the input filename in fine print
    if input_filename:
        specimen_id_text = f"{specimen_id}  <font size='8' color='grey'><i>(Source: {os.path.basename(input_filename)})</i></font>"
    else:
        specimen_id_text = specimen_id
    specimen_id_paragraph = Paragraph(specimen_id_text, patient_style)

    specimen_data = [
        [Paragraph("Specimen Type:", patient_bold_style), Paragraph(SPECIMEN_TYPE, patient_style)],
        [Paragraph("Specimen ID:", patient_bold_style), specimen_id_paragraph],
        [Paragraph("Collection Date:", patient_bold_style), Paragraph(collection_date, patient_style)],
        [Paragraph("Collected By:", patient_bold_style), Paragraph(collected_by, patient_style)],
        [Paragraph("Test Completed Date:", patient_bold_style), Paragraph(completed_date, patient_style)],
    ]
    specimen_table = Table(
        specimen_data,
        colWidths=[PDF_SPECIMEN_LABEL_WIDTH * inch, PDF_SPECIMEN_VALUE_WIDTH * inch]
    )
    specimen_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
    ]))

    return [
        patient_header, patient_table,
        Spacer(1, PDF_SPACER_MEDIUM*inch),
        specimen_header, specimen_table
    ]

def get_conditional_note():
    """Creates a small, italicized note for reports with positive results.

    Returns:
        reportlab.platypus.Paragraph: A styled paragraph object for the note.
    """
    style_factory = PDFStyleFactory()
    note_style = style_factory.create_note_style()
    note = Paragraph("*note: this sample contains a positive result*", note_style)
    return note

def get_results_table(sample_group):
    """Creates and formats the main table of test results.

    This function takes the patient sample data and formats it into a structured
    table, including a header row and all test results for that sample.

    Args:
        sample_group (pd.DataFrame): A DataFrame containing all test results
            for a single patient sample.

    Returns:
        list: A list of ReportLab Flowables containing the table header and the
            formatted table.
    """
    header = [Paragraph("<b>Test Name</b>"), Paragraph("<b>Result</b>"), Paragraph("<b>Units</b>"), Paragraph("<b>Flags</b>"), Paragraph("<b>COMMENTS</b>")]

    # Prepare data, ensuring all values are strings
    data = [header]
    for _, row in sample_group.iterrows():
        data.append([
            safe_str(row['Test Name']),
            safe_str(row['Test result']),
            safe_str(row['Test units']),
            safe_str(row['Flags']),
            safe_str(row['Comment'])
        ])

    table = Table(
        data,
        colWidths=[
            PDF_RESULTS_TEST_NAME_WIDTH * inch,
            PDF_RESULTS_RESULT_WIDTH * inch,
            PDF_RESULTS_UNITS_WIDTH * inch,
            PDF_RESULTS_FLAGS_WIDTH * inch,
            PDF_RESULTS_COMMENTS_WIDTH * inch
        ],
        repeatRows=1
    )

    style = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), lightgrey),
        ('TEXTCOLOR', (0,0), (-1,0), black),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('ALIGN', (0,1), (0,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('BACKGROUND', (0,1), (-1,-1), (1,1,1)),
        ('GRID', (0,0), (-1,-1), 1, black)
    ])
    table.setStyle(style)

    # Add "Test Information" header above the table
    style_factory = PDFStyleFactory()
    table_header_style = style_factory.create_table_header_style()
    table_header = Paragraph("Test Information", table_header_style)

    return [table_header, table]



if __name__ == '__main__':  # pragma: no cover
    # This block is for testing the PDF generation directly.
    from data_processor import load_and_process_data
    from run_summary import RunSummary

    summary = RunSummary()
    input_file = 'data/Test_Data.csv'
    grouped_samples = load_and_process_data(input_file, summary)

    if grouped_samples:
        print("Generating test PDFs for each sample...")
        output_dir = 'output_pdfs_test'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        for (mrn, date_collected), sample_group in grouped_samples:
            patient_info = sample_group.iloc[0]
            patient_name = str(patient_info['Name']).replace(' ', '-')
            collection_date = pd.to_datetime(date_collected).strftime('%Y-%m-%d')

            # Calculate completed date for the test run
            try:
                latest_completion_ts = pd.to_datetime(sample_group['Test completed']).max()
                completed_date_for_pdf = latest_completion_ts.strftime('%m/%d/%Y')
            except (ValueError, TypeError):
                raw_date = sample_group['Test completed'].iloc[0] if not sample_group['Test completed'].empty else "N/A"
                completed_date_for_pdf = str(raw_date).split(' ')[0]

            output_filename = f"{output_dir}/{patient_name}_{mrn}_{collection_date}.pdf"

            print(f"  - Generating report for {patient_name}...")
            generate_pdf_report(sample_group, output_filename, summary, completed_date_for_pdf)
            print(f"    ...saved to {output_filename}")

        print("Test PDF generation complete.")


def generate_positives_summary_pdf(summary, output_dir):
    """Generates a summary PDF of all positive results from the run.

    Args:
        summary (RunSummary): The summary object containing the collected positive results.
        output_dir (str): The directory to save the summary PDF in.
    """
    if not summary.positive_results:
        return  # No positive results to report

    output_filename = os.path.join(output_dir, POSITIVES_SUMMARY_FILENAME)
    doc = SimpleDocTemplate(
        output_filename,
        pagesize=letter,
        rightMargin=PDF_MARGIN*inch,
        leftMargin=PDF_MARGIN*inch,
        topMargin=PDF_MARGIN*inch,
        bottomMargin=PDF_MARGIN*inch
    )
    story = []
    style_factory = PDFStyleFactory()

    # --- Title ---
    title_style = style_factory.create_title_style()
    title = Paragraph("Summary of Positive Results", title_style)
    story.append(title)
    story.append(Spacer(1, PDF_SPACER_MEDIUM * inch))

    # --- Introduction ---
    intro_text = f"This report summarizes all <b>{len(summary.positive_results)}</b> positive results detected during the run."
    intro_style = style_factory.create_intro_style()
    story.append(Paragraph(intro_text, intro_style))
    story.append(Spacer(1, PDF_SPACER_MEDIUM * inch))

    # --- Results Table ---
    header = [
        Paragraph("<b>Patient Name</b>"),
        Paragraph("<b>MRN</b>"),
        Paragraph("<b>Collection Date</b>"),
        Paragraph("<b>Positive Test</b>")
    ]
    data = [header]

    # Sort results for consistency
    sorted_positives = sorted(summary.positive_results, key=lambda x: (x['patient_name'], x['mrn'], x['collection_date']))

    for result in sorted_positives:
        data.append([
            str(result['patient_name']),
            str(result['mrn']),
            str(result['collection_date']),
            str(result['test_name'])
        ])

    table = Table(
        data,
        colWidths=[
            PDF_POSITIVES_NAME_WIDTH * inch,
            PDF_POSITIVES_MRN_WIDTH * inch,
            PDF_POSITIVES_DATE_WIDTH * inch,
            PDF_POSITIVES_TEST_WIDTH * inch
        ],
        repeatRows=1
    )
    style = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), lightgrey),
        ('TEXTCOLOR', (0,0), (-1,0), black),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('GRID', (0,0), (-1,-1), 1, black)
    ])
    table.setStyle(style)
    story.append(table)

    doc.build(story)