"""This module is responsible for generating PDF reports from processed data.

It uses the reportlab library to construct a PDF document containing a laboratory
report for a single patient sample. The module defines functions to create
various components of the report, such as headers, footers, patient information
tables, and test result tables.
"""
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.colors import black, lightgrey
from reportlab.lib.units import inch
import pandas as pd
from datetime import datetime

def generate_pdf_report(sample_group, output_filename):
    """Generates and saves a complete PDF report for a single patient sample.

    This function orchestrates the creation of a PDF document by assembling
    various components (header, title, info tables, results, footer). It takes a
    DataFrame group corresponding to a single sample and saves the generated
    PDF to the specified file.

    Args:
        sample_group (pd.DataFrame): A DataFrame containing all data rows for a
            single, unique patient sample.
        output_filename (str): The path (including filename) where the
            generated PDF report will be saved.
    """
    doc = SimpleDocTemplate(output_filename, pagesize=letter,
                            rightMargin=inch, leftMargin=inch,
                            topMargin=inch, bottomMargin=inch)
    story = []
    styles = getSampleStyleSheet()

    # Get consistent patient info from the first row of the group
    patient_info = sample_group.iloc[0]

    # --- 1. Laboratory Header ---
    story.extend(get_lab_header())
    story.append(Spacer(1, 0.2 * inch))

    # --- 2. Report Title ---
    story.append(get_report_title())
    story.append(Spacer(1, 0.2 * inch))

    # --- 3. Patient and Specimen Info ---
    story.extend(get_info_tables(patient_info, sample_group))
    story.append(Spacer(1, 0.2 * inch))

    # --- 4. Conditional Positive Note ---
    if 'Positive' in sample_group['Test result'].values:
        story.append(get_conditional_note())
        story.append(Spacer(1, 0.1 * inch))

    # --- 5. Test Results Table ---
    story.extend(get_results_table(sample_group))

    # --- 6. Footer ---
    story.append(Spacer(1, 0.5 * inch))
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
    styles = getSampleStyleSheet()
    footer_header_style = ParagraphStyle('footer_header', parent=styles['h2'], fontName='Helvetica-Bold', fontSize=12, alignment=TA_LEFT)
    footer_text_style = ParagraphStyle('footer_text', parent=styles['Normal'], fontName='Helvetica', fontSize=10, leading=12)

    footer_header = Paragraph("interpretation of results", footer_header_style)

    p1_text = "<b>Negative :</b> The absence of the drug/drug metabolite in the sample at or above the cut-off concentration of the assay."
    p2_text = "<b>Positive :</b> The presence of drug/drug metabolite in the sample at or above the cut-off concentration of the assay."
    p3_text = "<b>Note :</b> The results of this test are to be used for clinical purposes only. This is a presumptive test. It is recommended that a more specific confirmatory test be used to confirm a positive result."

    p1 = Paragraph(p1_text, footer_text_style)
    p2 = Paragraph(p2_text, footer_text_style)
    p3 = Paragraph(p3_text, footer_text_style)

    return [footer_header, Spacer(1, 0.1*inch), p1, Spacer(1, 0.1*inch), p2, Spacer(1, 0.1*inch), p3]


def get_lab_header():
    """Creates and returns the main header for the laboratory report.

    The header includes the laboratory's name, CLIA ID, address, contact
    information, and the name of the laboratory director, followed by a
    horizontal line.

    Returns:
        list: A list of ReportLab Flowables representing the formatted header.
    """
    styles = getSampleStyleSheet()
    header_text = "Therapeutic Life Choices, LLC | CLIA ID: 37D2301589 | 1728 S Carson Ave | Tulsa, OK 74119 | p. (918) 917-4321 | e. drvadim@abraxaslabs.org | Laboratory Director: Vadim Yerokhin, PhD"
    header_style = ParagraphStyle('header_style', parent=styles['Normal'], fontSize=8, alignment=TA_LEFT)
    header = Paragraph(header_text, header_style)
    # The horizontal line will be drawn directly on the canvas in a more advanced setup.
    # For SimpleDocTemplate, we can simulate it with a table.
    line = Table([['']], colWidths=[6.5*inch], style=TableStyle([('LINEBELOW', (0,0), (-1,-1), 1, black)]))
    return [header, line]


def get_report_title():
    """Creates and returns the main title of the report.

    Returns:
        reportlab.platypus.Paragraph: A styled paragraph object for the title.
    """
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('title_style', parent=styles['h1'], fontSize=14, alignment=TA_CENTER, fontName='Helvetica-Bold')
    title = Paragraph("urine drug test results", title_style)
    return title

def get_info_tables(patient_info, sample_group):
    """Creates the patient and specimen information tables.

    This function constructs two formatted tables: one for patient demographics
    (Name, DOB, MRN) and one for specimen details (Type, ID, Collection Date,
    etc.).

    Args:
        patient_info (pd.Series): A pandas Series containing the demographic
            information for the patient. It's expected to be the first row
            of the sample group.
        sample_group (pd.DataFrame): The DataFrame for the entire sample, used
            to derive the 'Test Completed Date'.

    Returns:
        list: A list of ReportLab Flowables, including headers and tables for
            patient and specimen information.
    """
    styles = getSampleStyleSheet()
    # Base styles
    patient_style = ParagraphStyle('patient_style', parent=styles['Normal'], fontName='Helvetica', fontSize=10)
    patient_bold_style = ParagraphStyle('patient_bold_style', parent=patient_style, fontName='Helvetica-Bold')
    info_header_style = ParagraphStyle('info_header', parent=styles['h2'], fontName='Helvetica-Bold', fontSize=12, alignment=TA_LEFT)

    # --- Patient Information Block ---
    patient_header = Paragraph("Patient Information", info_header_style)
    patient_data = [
        [Paragraph("Patient Name", patient_bold_style), Paragraph("DOB", patient_bold_style), Paragraph("Patient id", patient_bold_style)],
        [Paragraph(patient_info['Name'], patient_style), Paragraph(patient_info['Date of Birth'], patient_style), Paragraph(patient_info['MR#'], patient_style)]
    ]
    patient_table = Table(patient_data, colWidths=[2.16*inch, 2.16*inch, 2.16*inch])
    patient_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
    ]))

    # --- Specimen Information Block ---
    specimen_header = Paragraph("Specimen Information", info_header_style)
    # Derive completed date
    latest_completion_ts = pd.to_datetime(sample_group['Test completed'], format='%m/%d/%Y %I:%M:%S %p').max()
    completed_date = latest_completion_ts.strftime('%m/%d/%Y')

    specimen_data = [
        [Paragraph("Specimen Type:", patient_bold_style), Paragraph("Urine", patient_style)],
        [Paragraph("Specimen ID:", patient_bold_style), Paragraph(str(patient_info['ID']), patient_style)],
        [Paragraph("Collection Date:", patient_bold_style), Paragraph(patient_info['Date collected'], patient_style)],
        [Paragraph("Collected By:", patient_bold_style), Paragraph(patient_info['Collected by'], patient_style)],
        [Paragraph("Test Completed Date:", patient_bold_style), Paragraph(completed_date, patient_style)],
    ]
    specimen_table = Table(specimen_data, colWidths=[1.6*inch, 4.9*inch])
    specimen_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
    ]))

    return [patient_header, patient_table, Spacer(1, 0.2*inch), specimen_header, specimen_table]

def get_conditional_note():
    """Creates a small, italicized note for reports with positive results.

    Returns:
        reportlab.platypus.Paragraph: A styled paragraph object for the note.
    """
    styles = getSampleStyleSheet()
    note_style = ParagraphStyle('note_style', parent=styles['Normal'], fontName='Helvetica-Oblique', fontSize=10)
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
            row['Test Name'],
            row['Test result'],
            row['Test units'] if pd.notna(row['Test units']) else '',
            row['Flags'] if pd.notna(row['Flags']) else '',
            row['Comment'] if pd.notna(row['Comment']) else ''
        ])

    table = Table(data, colWidths=[2.5*inch, 1*inch, 1*inch, 1*inch, 1*inch], repeatRows=1)

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
    styles = getSampleStyleSheet()
    table_header_style = ParagraphStyle('table_header', parent=styles['h2'], fontName='Helvetica-Bold', fontSize=12, alignment=TA_LEFT)
    table_header = Paragraph("Test Information", table_header_style)

    return [table_header, table]



if __name__ == '__main__':
    # This block is for testing the PDF generation directly.
    # We will need to load the data first.
    from data_processor import load_and_process_data

    input_file = 'data/Test_Data.csv'
    grouped_samples = load_and_process_data(input_file)

    if grouped_samples:
        print("Generating test PDFs for each sample...")
        output_dir = 'output_pdfs'
        import os
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        for (sample_id, date_collected), sample_group in grouped_samples:
            patient_name = sample_group['Name'].iloc[0].replace(' ', '-')
            mrn = sample_group['MR#'].iloc[0]
            collection_date = pd.to_datetime(date_collected).strftime('%Y-%m-%d')

            output_filename = f"{output_dir}/{patient_name}_{mrn}_{collection_date}.pdf"

            print(f"  - Generating report for {patient_name}...")
            generate_pdf_report(sample_group, output_filename)
            print(f"    ...saved to {output_filename}")

        print("Test PDF generation complete.")