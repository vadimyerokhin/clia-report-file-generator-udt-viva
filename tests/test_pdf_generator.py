import unittest
import os
import pandas as pd
from reportlab.platypus import Paragraph, Table, Spacer

from src.data_processor import load_and_process_data
from src.pdf_generator import (
    get_lab_header,
    get_report_title,
    get_info_tables,
    get_conditional_note,
    get_results_table,
    get_footer,
    generate_pdf_report,
)


class TestPdfGenerator(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Load data once for all tests."""
        cls.test_data_dir = 'tests/test_data'
        cls.good_csv_path = os.path.join(cls.test_data_dir, 'sample_data.csv')

        grouped_data = load_and_process_data(cls.good_csv_path)
        cls.positive_sample_group = grouped_data.get_group((1, '2023-01-15'))
        cls.negative_sample_group = grouped_data.get_group((2, '2023-01-16'))
        cls.patient_info_positive = cls.positive_sample_group.iloc[0]
        cls.patient_info_negative = cls.negative_sample_group.iloc[0]

    def test_get_lab_header(self):
        """Test that the lab header is created correctly."""
        header = get_lab_header()
        self.assertEqual(len(header), 2)
        self.assertIsInstance(header[0], Paragraph)
        self.assertIsInstance(header[1], Table)
        self.assertIn("Therapeutic Life Choices, LLC", header[0].text)

    def test_get_report_title(self):
        """Test that the report title is created correctly."""
        title = get_report_title()
        self.assertIsInstance(title, Paragraph)
        self.assertEqual(title.text.lower(), "urine drug test results")

    def test_get_info_tables(self):
        """Test that patient and specimen info tables are created correctly."""
        info_tables = get_info_tables(self.patient_info_positive, self.positive_sample_group)
        self.assertEqual(len(info_tables), 5)
        # Check for patient name in the patient table
        patient_table = info_tables[1]
        self.assertIn(self.patient_info_positive['Name'], patient_table._cellvalues[1][0].text)
        # Check for specimen ID in the specimen table
        specimen_table = info_tables[4]
        self.assertIn(str(self.patient_info_positive['ID']), specimen_table._cellvalues[1][1].text)

    def test_get_conditional_note(self):
        """Test the conditional note for positive results."""
        # Test that note is present for a positive sample
        note = get_conditional_note()
        self.assertIsInstance(note, Paragraph)
        self.assertIn("positive result", note.text)

    def test_get_results_table(self):
        """Test that the results table is created correctly."""
        results_table_flowables = get_results_table(self.positive_sample_group)
        self.assertEqual(len(results_table_flowables), 2)

        header_paragraph = results_table_flowables[0]
        self.assertIsInstance(header_paragraph, Paragraph)
        self.assertEqual(header_paragraph.text, "Test Information")

        table = results_table_flowables[1]
        self.assertIsInstance(table, Table)
        # 4 rows in table = 1 header + 3 data rows
        self.assertEqual(len(table._cellvalues), 4)
        # Check for a specific test name
        self.assertEqual(table._cellvalues[1][0], 'Opiates')

    def test_get_footer(self):
        """Test that the footer is created correctly."""
        footer = get_footer()
        self.assertTrue(len(footer) > 3)
        self.assertIsInstance(footer[0], Paragraph)
        self.assertEqual(footer[0].text.lower(), "interpretation of results")
        self.assertIsInstance(footer[2], Paragraph)
        self.assertIn("Negative", footer[2].text)

    def test_generate_pdf_report_runs_without_error(self):
        """Test that the main PDF generation function runs without crashing."""
        output_dir = 'tests/output_pdfs'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        output_filename = os.path.join(output_dir, 'test_report.pdf')
        try:
            generate_pdf_report(self.positive_sample_group, output_filename)
            self.assertTrue(os.path.exists(output_filename))
        finally:
            # Clean up the created file
            if os.path.exists(output_filename):
                os.remove(output_filename)
            if os.path.exists(output_dir):
                os.rmdir(output_dir)

if __name__ == '__main__':
    unittest.main()