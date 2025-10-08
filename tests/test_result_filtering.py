import unittest
from unittest.mock import patch
import pandas as pd
from io import StringIO
import sys
import os

from src.data_processor import load_and_process_data
from src.pdf_generator import generate_pdf_report
from src.run_summary import RunSummary

class TestResultFiltering(unittest.TestCase):

    def setUp(self):
        """Set up test data and environment."""
        self.summary = RunSummary()
        self.invalid_data_path = 'data/invalid_results_data.csv'
        self.output_filename = 'test_report.pdf'

        # --- Data for new tests ---
        self.base_patient_info = {
            'Type': 'Patient', 'ID': 100, 'Date collected': '2023-02-01',
            'Name': 'Test Patient', 'MR#': 'MRN100', 'Date of Birth': '01/01/1990',
            'Collected by': 'Tester', 'Test completed': '02/01/2023 12:00:00 PM',
            'Test units': 'ng/mL', 'Flags': '', 'Comment': ''
        }

        # 1. Data with no valid results
        no_valid_data = [{'Test Name': 'Test A', 'Test result': 'PENDING'}]
        self.no_valid_results_df = pd.DataFrame([{**self.base_patient_info, **d} for d in no_valid_data])

        # 2. Case-insensitive data
        case_data = [
            {'Test Name': 'Test A', 'Test result': 'Positive'},
            {'Test Name': 'Test B', 'Test result': 'negative'},
            {'Test Name': 'Test C', 'Test result': 'POSITIVE'},
            {'Test Name': 'Test D', 'Test result': 'Invalid'},
        ]
        self.case_insensitive_df = pd.DataFrame([{**self.base_patient_info, **d} for d in case_data])

        # 3. Mixed data types
        mixed_data = [
            {'Test Name': 'Test A', 'Test result': 'Positive'},
            {'Test Name': 'Test B', 'Test result': None},
            {'Test Name': 'Test C', 'Test result': 123},
            {'Test Name': 'Test D', 'Test result': 'Negative'},
        ]
        self.mixed_types_df = pd.DataFrame([{**self.base_patient_info, **d} for d in mixed_data])

    def tearDown(self):
        """Clean up generated files."""
        if os.path.exists(self.output_filename):
            os.remove(self.output_filename)

    @patch('src.pdf_generator.get_results_table')
    def test_invalid_results_are_filtered_and_logged(self, mock_get_results_table):
        """
        Verify that results other than 'Positive' or 'Negative' are filtered out
        and logged to the RunSummary object.
        """
        grouped_samples = load_and_process_data(self.invalid_data_path, self.summary)
        self.assertIsNotNone(grouped_samples, "Data loading failed.")

        jane_doe_sample = next((group for (mrn, _), group in grouped_samples if mrn == 'DOE-J-1985'), None)
        self.assertIsNotNone(jane_doe_sample, "Test sample for 'JANE DOE' not found.")

        generate_pdf_report(jane_doe_sample, self.output_filename, self.summary)

        # Check that the invalid result was logged to the summary object
        self.assertIn('DOE-J-1985', self.summary._invalid_results)
        self.assertIn("Barbiturates: 'PENDING'", self.summary._invalid_results['DOE-J-1985'])
        self.assertIn("Fentanyl 1: 'ERROR'", self.summary._invalid_results['DOE-J-1985'])

        # Check that the valid results were still passed to the table generator
        self.assertTrue(mock_get_results_table.called)
        filtered_sample_group = mock_get_results_table.call_args[0][0]
        self.assertEqual(len(filtered_sample_group), 2)
        self.assertTrue(all(item in ['Positive', 'Negative'] for item in filtered_sample_group['Test result']))

    @patch('src.pdf_generator.get_results_table')
    def test_filtering_with_no_valid_results(self, mock_get_results_table):
        """Test that when no results are valid, the results table is not generated."""
        generate_pdf_report(self.no_valid_results_df, self.output_filename, self.summary)

        # The results table should not be created if there are no valid results
        mock_get_results_table.assert_not_called()

    @patch('src.pdf_generator.get_results_table')
    def test_case_insensitive_filtering(self, mock_get_results_table):
        """Test that filtering is case-insensitive for 'Positive' and 'Negative'."""
        generate_pdf_report(self.case_insensitive_df, self.output_filename, self.summary)

        mock_get_results_table.assert_called_once()
        filtered_df = mock_get_results_table.call_args[0][0]

        self.assertEqual(len(filtered_df), 3)
        self.assertTrue(all(r.lower() in ['positive', 'negative'] for r in filtered_df['Test result']))

    @patch('src.pdf_generator.get_results_table')
    def test_mixed_data_types_in_result_column(self, mock_get_results_table):
        """Test filtering with mixed data types in the 'Test result' column."""
        generate_pdf_report(self.mixed_types_df, self.output_filename, self.summary)

        mock_get_results_table.assert_called_once()
        filtered_df = mock_get_results_table.call_args[0][0]

        self.assertEqual(len(filtered_df), 2)
        self.assertIn('Positive', filtered_df['Test result'].values)
        self.assertIn('Negative', filtered_df['Test result'].values)

if __name__ == '__main__':
    unittest.main()