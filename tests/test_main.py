import os
import sys
import shutil
import unittest
from unittest.mock import patch, MagicMock

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from main import main

class TestMain(unittest.TestCase):

    def setUp(self):
        """Set up a temporary directory for test outputs."""
        self.output_dir = "temp_test_output"
        # Ensure the directory is clean before each test
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)

    def tearDown(self):
        """Remove the temporary directory after tests."""
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)

    @patch('builtins.input', side_effect=['2'])  # Simulate user choosing the second option
    def test_conflict_resolution_flow(self, mock_input):
        """Test the full flow with a data file containing a conflict."""
        input_file = "tests/test_data/conflict_data.csv"
        main(input_file, self.output_dir)

        # Check that only one report was generated for the conflict patient
        expected_filename = "Conflict-Patient_MRN006_2023-01-20.pdf"
        output_files = os.listdir(self.output_dir)

        # There should be 3 reports in total: one for MRN001, one for MRN002, and one for MRN006
        self.assertEqual(len(output_files), 3, "Should generate three reports in total.")

        # Check that the specific, user-selected report exists
        self.assertIn(expected_filename, output_files, "The PDF for the selected conflicted sample should be generated.")

    def test_output_directory_creation(self):
        """Test that the output directory is created if it does not exist."""
        self.assertFalse(os.path.exists(self.output_dir))
        input_file = "tests/test_data/sample_data.csv"
        main(input_file, self.output_dir)
        self.assertTrue(os.path.exists(self.output_dir))

    @patch('src.main.load_and_process_data', return_value=None)
    def test_no_data_loaded(self, mock_load_data):
        """Test that the script exits gracefully if no data is loaded."""
        input_file = "tests/test_data/empty_data.csv"
        main(input_file, self.output_dir)
        # The directory is created, but should be empty.
        self.assertTrue(os.path.exists(self.output_dir))
        self.assertEqual(len(os.listdir(self.output_dir)), 0)

    @patch('builtins.input', side_effect=['a', '3', '1'])  # Invalid, out of range, then valid
    def test_invalid_user_input_for_conflict(self, mock_input):
        """Test handling of invalid and out-of-range user input."""
        input_file = "tests/test_data/conflict_data.csv"
        main(input_file, self.output_dir)
        # Check that the first valid choice was processed
        output_files = os.listdir(self.output_dir)
        self.assertIn("Conflict-Patient_MRN006_2023-01-20.pdf", output_files)
        self.assertEqual(mock_input.call_count, 3)

    @patch('builtins.input', side_effect=KeyboardInterrupt)
    def test_user_cancellation_during_conflict(self, mock_input):
        """Test that user cancellation (Ctrl+C) is handled gracefully."""
        input_file = "tests/test_data/conflict_data.csv"
        main(input_file, self.output_dir)
        # The conflict patient should be skipped, but other reports generated
        output_files = os.listdir(self.output_dir)
        self.assertEqual(len(output_files), 2)
        self.assertNotIn("Conflict-Patient_MRN006_2023-01-20.pdf", output_files)

    def test_malformed_date_handling(self):
        """Test that a malformed date does not crash the application."""
        malformed_date_file = os.path.join("tests/test_data", "malformed_date_data.csv")
        with open(malformed_date_file, 'w') as f:
            f.write("Type,ID,Date collected,Name,MR#,Date of Birth,Collected by,Test completed,Test Name,Test result,Test units,Flags,Comment\n")
            f.write("Patient,1,NOT-A-DATE,Bad Date Patient,MRN-DATE,01/01/1990,Collector,01/15/2023 12:00:00 PM,Test,Positive,ng/mL,,\n")

        try:
            main(malformed_date_file, self.output_dir)
            expected_filename = "Bad-Date-Patient_MRN-DATE_NOT-A-DATE.pdf"
            self.assertIn(expected_filename, os.listdir(self.output_dir))
        finally:
            if os.path.exists(malformed_date_file):
                os.remove(malformed_date_file)

    @patch('main.generate_pdf_report', side_effect=Exception("PDF Generation Failed"))
    def test_pdf_generation_error_handling(self, mock_generate_pdf):
        """Test that an error during PDF generation is caught and logged."""
        input_file = "tests/test_data/sample_data.csv"
        main(input_file, self.output_dir)
        # The error should be printed, but the process should complete for other files
        self.assertEqual(mock_generate_pdf.call_count, 4)
        # No files should be created because the mock always raises an exception
        self.assertEqual(len(os.listdir(self.output_dir)), 0)

if __name__ == '__main__':  # pragma: no cover
    unittest.main()