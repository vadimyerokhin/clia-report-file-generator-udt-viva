import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from io import StringIO
import sys

from src.data_processor import load_and_process_data
from src.pdf_generator import generate_pdf_report

class TestResultFiltering(unittest.TestCase):

    def setUp(self):
        """Set up test data and environment."""
        self.invalid_data_path = 'data/invalid_results_data.csv'
        self.output_filename = 'test_report.pdf'

    @patch('src.pdf_generator.get_results_table')
    def test_invalid_results_are_filtered_and_warning_is_printed(self, mock_get_results_table):
        """
        Verify that results other than 'Positive' or 'Negative' are filtered out
        before PDF generation and a warning is printed to the console.
        """
        # Load the data with invalid results
        grouped_samples = load_and_process_data(self.invalid_data_path)
        self.assertIsNotNone(grouped_samples, "Data loading failed.")

        # Capture stdout to check for the warning message
        captured_output = StringIO()
        sys.stdout = captured_output

        # Find the specific sample group for Jane Doe
        jane_doe_sample = None
        for (mrn, date_collected), group in grouped_samples:
            if mrn == 'DOE-J-1985':
                jane_doe_sample = group
                break

        self.assertIsNotNone(jane_doe_sample, "Test sample for 'JANE DOE' not found.")

        # Generate the report for this sample
        generate_pdf_report(jane_doe_sample, self.output_filename)

        # Restore stdout
        sys.stdout = sys.__stdout__

        # 1. Check if the warning was printed
        output = captured_output.getvalue()
        self.assertIn("Warning: Invalid results found for patient MR# DOE-J-1985", output)
        self.assertIn("Barbiturates: PENDING", output)
        self.assertIn("Fentanyl 1: ERROR", output)

        # 2. Check that get_results_table was called with filtered data
        self.assertTrue(mock_get_results_table.called, "get_results_table was not called.")
        call_args, _ = mock_get_results_table.call_args
        filtered_sample_group = call_args[0]

        # The filtered group should only contain 'Positive' and 'Negative' results
        self.assertEqual(len(filtered_sample_group), 2)
        valid_results = ['Positive', 'Negative']
        self.assertTrue(all(item in valid_results for item in filtered_sample_group['Test result']))
        self.assertFalse('PENDING' in filtered_sample_group['Test result'].values)
        self.assertFalse('ERROR' in filtered_sample_group['Test result'].values)

if __name__ == '__main__':
    unittest.main()