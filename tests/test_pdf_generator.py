import unittest
import os
import sys
import pandas as pd
from io import StringIO
from unittest.mock import patch
from reportlab.platypus import Paragraph, Table, Spacer

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from data_processor import load_and_process_data
from pdf_generator import (
    get_lab_header,
    get_report_title,
    get_info_tables,
    get_conditional_note,
    get_results_table,
    get_footer,
    generate_pdf_report,
)
from src.run_summary import RunSummary


class TestPdfGenerator(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Load data once for all tests."""
        cls.summary = RunSummary()
        cls.test_data_dir = 'tests/test_data'
        cls.good_csv_path = os.path.join(cls.test_data_dir, 'sample_data.csv')

        grouped_data = load_and_process_data(cls.good_csv_path, cls.summary)
        cls.positive_sample_group = grouped_data.get_group(('MRN001', '2023-01-15'))
        cls.negative_sample_group = grouped_data.get_group(('MRN002', '2023-01-16'))
        cls.patient_info_positive = cls.positive_sample_group.iloc[0]
        cls.patient_info_negative = cls.negative_sample_group.iloc[0]

        # --- Create custom data for edge cases ---
        # 1. Sample with no valid results
        no_valid_data = {
            'Type': ['Patient'], 'ID': [99], 'Date collected': ['2023-01-25'],
            'Name': ['No-Result Patient'], 'MR#': ['MRN999'], 'Date of Birth': ['01/01/1990'],
            'Collected by': ['Tester'], 'Test completed': ['01/25/2023 12:00:00 PM'],
            'Test Name': ['Test A'], 'Test result': ['Invalid'], 'Test units': ['ng/mL'],
            'Flags': [''], 'Comment': ['']
        }
        cls.no_valid_results_group = pd.DataFrame(no_valid_data)

        # 2. Sample with missing optional fields (Comment, Flags)
        missing_optional_data = {
            'Type': ['Patient'], 'ID': [98], 'Date collected': ['2023-01-26'],
            'Name': ['Missing-Optional Patient'], 'MR#': ['MRN998'], 'Date of Birth': ['01/01/1990'],
            'Collected by': ['Tester'], 'Test completed': ['01/26/2023 12:00:00 PM'],
            'Test Name': ['Test B'], 'Test result': ['Positive'], 'Test units': ['ng/mL'],
            'Flags': [None], 'Comment': [None]
        }
        cls.missing_optional_fields_group = pd.DataFrame(missing_optional_data)

        # 3. Sample with case-insensitive results
        case_insensitive_data = {
            'Type': ['Patient'], 'ID': [97], 'Date collected': ['2023-01-27'],
            'Name': ['Case-Sensitive Patient'], 'MR#': ['MRN997'], 'Date of Birth': ['01/01/1990'],
            'Collected by': ['Tester'], 'Test completed': ['01/27/2023 12:00:00 PM'],
            'Test Name': ['Test C'], 'Test result': ['positive'], 'Test units': ['ng/mL'],
            'Flags': [''], 'Comment': ['']
        }
        cls.case_insensitive_group = pd.DataFrame(case_insensitive_data)

        # 4. Sample with missing critical data (e.g., patient name)
        missing_critical_data = {
            'Type': ['Patient'], 'ID': [96], 'Date collected': ['2023-01-28'],
            'Name': [None], 'MR#': ['MRN996'], 'Date of Birth': ['01/01/1990'],
            'Collected by': ['Tester'], 'Test completed': ['01/28/2023 12:00:00 PM'],
            'Test Name': ['Test D'], 'Test result': ['Negative'], 'Test units': ['ng/mL'],
            'Flags': [''], 'Comment': ['']
        }
        cls.missing_critical_group = pd.DataFrame(missing_critical_data)

    def setUp(self):
        """Set up for each test case."""
        self.summary = RunSummary()

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
        info_tables = get_info_tables(self.patient_info_positive, self.positive_sample_group, self.summary)
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
            generate_pdf_report(self.positive_sample_group, output_filename, self.summary)
            self.assertTrue(os.path.exists(output_filename))
        finally:
            # Clean up the created file
            if os.path.exists(output_filename):
                os.remove(output_filename)
            if os.path.exists(output_dir) and not os.listdir(output_dir):
                os.rmdir(output_dir)

    def test_sample_with_no_valid_results(self):
        """Test that a report is still generated if a sample has no valid results."""
        output_dir = 'tests/output_pdfs'
        os.makedirs(output_dir, exist_ok=True)
        output_filename = os.path.join(output_dir, 'no_valid_results_report.pdf')

        try:
            generate_pdf_report(self.no_valid_results_group, output_filename, self.summary)
            self.assertTrue(os.path.exists(output_filename))
            # The results table should be empty, so we can check the story length or content
        finally:
            if os.path.exists(output_filename):
                os.remove(output_filename)
            if os.path.exists(output_dir) and not os.listdir(output_dir):
                os.rmdir(output_dir)

    def test_missing_optional_fields(self):
        """Test PDF generation when optional fields like 'Comment' and 'Flags' are missing."""
        output_dir = 'tests/output_pdfs'
        os.makedirs(output_dir, exist_ok=True)
        output_filename = os.path.join(output_dir, 'missing_optional_fields_report.pdf')

        try:
            generate_pdf_report(self.missing_optional_fields_group, output_filename, self.summary)
            self.assertTrue(os.path.exists(output_filename))
        finally:
            if os.path.exists(output_filename):
                os.remove(output_filename)
            if os.path.exists(output_dir) and not os.listdir(output_dir):
                os.rmdir(output_dir)

    def test_case_insensitive_results_handling(self):
        """Test that 'positive' (lowercase) is handled correctly."""
        output_dir = 'tests/output_pdfs'
        os.makedirs(output_dir, exist_ok=True)
        output_filename = os.path.join(output_dir, 'case_insensitive_report.pdf')

        try:
            # This should generate a note because of the 'positive' result.
            generate_pdf_report(self.case_insensitive_group, output_filename, self.summary)
            self.assertTrue(os.path.exists(output_filename))
        finally:
            if os.path.exists(output_filename):
                os.remove(output_filename)
            if os.path.exists(output_dir) and not os.listdir(output_dir):
                os.rmdir(output_dir)

    def test_missing_critical_data_handling(self):
        """Test that missing critical data (e.g., patient name) is handled without crashing."""
        output_dir = 'tests/output_pdfs'
        os.makedirs(output_dir, exist_ok=True)
        output_filename = os.path.join(output_dir, 'missing_critical_data_report.pdf')

        try:
            # The function should still run, but the name field in the PDF would be empty
            generate_pdf_report(self.missing_critical_group, output_filename, self.summary)
            self.assertTrue(os.path.exists(output_filename))
        finally:
            if os.path.exists(output_filename):
                os.remove(output_filename)
            if os.path.exists(output_dir) and not os.listdir(output_dir):
                os.rmdir(output_dir)

    def test_24_hour_timestamp_format_succeeds_after_fix(self):
        """Test that PDF generation succeeds with a 24-hour timestamp after the fix."""
        bug_csv_path = os.path.join(self.test_data_dir, 'bug_report_data.csv')
        grouped_data = load_and_process_data(bug_csv_path, self.summary)
        self.assertIsNotNone(grouped_data, "Failed to load bug report test data.")

        bug_sample_group = grouped_data.get_group(('BR001', '10/08/2025'))
        output_dir = 'tests/output_pdfs'
        os.makedirs(output_dir, exist_ok=True)
        output_filename = os.path.join(output_dir, 'bug_report_after_fix.pdf')

        try:
            # After the fix, this should run without raising a ValueError
            generate_pdf_report(bug_sample_group, output_filename, self.summary)
            self.assertTrue(os.path.exists(output_filename), "PDF report should be generated successfully.")
        finally:
            # Clean up any file that might have been created
            if os.path.exists(output_filename):
                os.remove(output_filename)
            if os.path.exists(output_dir) and not os.listdir(output_dir):
                os.rmdir(output_dir)


    def test_generate_pdf_with_bad_date_format(self):
        """Test PDF generation when 'Test completed' date is malformed."""
        data = {
            'Name': ['Bad Date Patient'],
            'Date of Birth': ['01/01/1990'],
            'MR#': ['MRN-DATE'],
            'ID': ['1'],
            'Date collected': ['2023-01-15'],
            'Collected by': ['Test Collector'],
            'Test completed': ['NOT-A-DATE'],
            'Test Name': ['Test A'],
            'Test result': ['Positive'],
            'Test units': [''],
            'Flags': [''],
            'Comment': ['']
        }
        sample_group = pd.DataFrame(data)
        output_dir = 'tests/output_pdfs'
        os.makedirs(output_dir, exist_ok=True)
        output_filename = os.path.join(output_dir, "test_bad_date.pdf")

        try:
            generate_pdf_report(sample_group, output_filename, self.summary)
            # Verify the error was logged to summary
            self.assertEqual(len(self.summary._errors), 1)
            self.assertIn("Could not parse 'Test completed' date", self.summary._errors[0])
            self.assertIn("MRN-DATE", self.summary._errors[0])
            # Verify the PDF was created
            self.assertTrue(os.path.exists(output_filename))
        finally:
            if os.path.exists(output_filename):
                os.remove(output_filename)
            if os.path.exists(output_dir) and not os.listdir(output_dir):
                os.rmdir(output_dir)


    def test_results_with_whitespace_are_handled(self):
        """Test that results with leading/trailing whitespace are correctly processed."""
        # Create data with whitespace in the 'Test result'
        whitespace_data = {
            'Type': ['Patient'], 'ID': [95], 'Date collected': ['2023-01-29'],
            'Name': ['Whitespace Patient'], 'MR#': ['MRN995'], 'Date of Birth': ['01/01/1990'],
            'Collected by': ['Tester'], 'Test completed': ['01/29/2023 12:00:00 PM'],
            'Test Name': ['Test E'], 'Test result': [' Positive '], 'Test units': ['ng/mL'],
            'Flags': [''], 'Comment': ['']
        }
        whitespace_group = pd.DataFrame(whitespace_data)

        output_dir = 'tests/output_pdfs'
        os.makedirs(output_dir, exist_ok=True)
        output_filename = os.path.join(output_dir, 'whitespace_report.pdf')

        # We want to check if the conditional note for positive results is added.
        # We can patch 'get_conditional_note' and assert it was called.
        with patch('pdf_generator.get_conditional_note') as mock_get_note:
            try:
                generate_pdf_report(whitespace_group, output_filename, self.summary)
                # Before the fix, this will fail because ' positive ' is not in the valid list.
                # After the fix, .strip() will be called, and it should be identified as positive.
                mock_get_note.assert_called_once()
            finally:
                if os.path.exists(output_filename):
                    os.remove(output_filename)
                # This rmdir might fail if other tests run async and create files,
                # so we check if it's empty first.
                if os.path.exists(output_dir) and not os.listdir(output_dir):
                    os.rmdir(output_dir)


if __name__ == '__main__':
    unittest.main()