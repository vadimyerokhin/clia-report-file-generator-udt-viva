import os
import sys
import shutil
import unittest
from unittest.mock import patch, MagicMock, ANY

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from main import main, generate_reports
from src.run_summary import RunSummary

class TestMain(unittest.TestCase):

    def setUp(self):
        """Set up a temporary directory for test outputs."""
        self.output_dir = "temp_test_output"
        self.test_data_dir = "tests/test_data"
        # Ensure the directories are clean before each test
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
        if not os.path.exists(self.test_data_dir):
            os.makedirs(self.test_data_dir)

    def tearDown(self):
        """Remove the temporary directory after tests."""
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)

    @patch('builtins.input', side_effect=['2'])  # Simulate user choosing the second option
    def test_conflict_resolution_flow(self, mock_input):
        """Test the full flow with a data file containing a conflict."""
        input_file = "tests/test_data/conflict_data.csv"
        main(input_file, self.output_dir, organize_by=None)

        # Check that only one report was generated for the conflict patient
        expected_filename = "Conflict-Patient_MRN006_2023-01-20.pdf"
        output_files = os.listdir(self.output_dir)

        # There should be 4 reports in total: one for MRN001, one for MRN002, one for MRN006, and the summary
        self.assertEqual(len(output_files), 4, "Should generate four reports in total.")

        # Check that the specific, user-selected report exists
        self.assertIn(expected_filename, output_files, "The PDF for the selected conflicted sample should be generated.")
        self.assertIn("positives_summary.pdf", output_files, "The positives summary PDF should be generated.")

    def test_output_directory_creation(self):
        """Test that the output directory is created if it does not exist."""
        self.assertFalse(os.path.exists(self.output_dir))
        input_file = "tests/test_data/sample_data.csv"
        main(input_file, self.output_dir, organize_by=None)
        self.assertTrue(os.path.exists(self.output_dir))

    @patch('main.load_and_process_data', return_value=None)
    def test_no_data_loaded(self, mock_load_data):
        """Test that the script exits gracefully if no data is loaded."""
        input_file = os.path.join(self.test_data_dir, "empty_data.csv")
        with open(input_file, 'w') as f:
            pass  # Create empty file

        main(input_file, self.output_dir, organize_by=None)

        self.assertTrue(os.path.exists(self.output_dir))
        self.assertEqual(len(os.listdir(self.output_dir)), 0)
        mock_load_data.assert_called_with(input_file, ANY)

        if os.path.exists(input_file):
            os.remove(input_file)

    @patch('builtins.input', side_effect=['a', '3', '1'])  # Invalid, out of range, then valid
    def test_invalid_user_input_for_conflict(self, mock_input):
        """Test handling of invalid and out-of-range user input."""
        input_file = "tests/test_data/conflict_data.csv"
        main(input_file, self.output_dir, organize_by=None)
        # Check that the first valid choice was processed
        output_files = os.listdir(self.output_dir)
        self.assertIn("Conflict-Patient_MRN006_2023-01-20.pdf", output_files)
        self.assertEqual(mock_input.call_count, 3)

    @patch('main.RunSummary')
    @patch('builtins.input', side_effect=['s'])
    def test_user_skipping_conflict(self, mock_input, mock_summary_class):
        """Test that user can skip a conflict with 's'."""
        mock_summary_instance = MagicMock()
        mock_summary_class.return_value = mock_summary_instance

        input_file = "tests/test_data/conflict_data.csv"
        main(input_file, self.output_dir, organize_by=None)

        # The conflict patient should be skipped, but summary is still generated
        output_files = os.listdir(self.output_dir)
        self.assertEqual(len(output_files), 3)
        self.assertNotIn("Conflict-Patient_MRN006_2023-01-20.pdf", output_files)

        # Check that the skip was logged
        mock_summary_instance.log_user_skip.assert_called_once_with('MRN006', '2023-01-20', ANY)

    @patch('main.RunSummary')
    def test_malformed_date_handling(self, mock_summary_class):
        """Test that a malformed date does not crash the application and is logged."""
        mock_summary_instance = MagicMock()
        mock_summary_instance._positive_results = []
        mock_summary_class.return_value = mock_summary_instance

        malformed_date_file = os.path.join(self.test_data_dir, "malformed_date_data.csv")
        with open(malformed_date_file, 'w') as f:
            f.write("Type,ID,Date collected,Name,MR#,Date of Birth,Collected by,Test completed,Test Name,Test result,Test units,Flags,Comment\n")
            f.write("Patient,1,NOT-A-DATE,Bad Date Patient,MRN-DATE,01/01/1990,Collector,01/15/2023 12:00:00 PM,Test,Positive,ng/mL,,\n")

        try:
            main(malformed_date_file, self.output_dir, organize_by=None)
            # The file should NOT be created
            self.assertEqual(len(os.listdir(self.output_dir)), 0)
            # The error should be logged
            mock_summary_instance.log_failure.assert_called_once_with(
                "MR# MRN-DATE", "The date 'NOT-A-DATE' in the 'Date collected' column could not be parsed."
            )
        finally:
            if os.path.exists(malformed_date_file):
                os.remove(malformed_date_file)

    @patch('main.RunSummary')
    @patch('main.generate_pdf_report', side_effect=Exception("PDF Generation Failed"))
    def test_pdf_generation_error_handling(self, mock_generate_pdf, mock_summary_class):
        """Test that an error during PDF generation is caught and logged."""
        mock_summary_instance = MagicMock()
        mock_summary_instance._positive_results = []
        mock_summary_class.return_value = mock_summary_instance

        input_file = "tests/test_data/sample_data.csv"
        main(input_file, self.output_dir, organize_by=None)

        # The error should be logged for each of the 4 samples
        self.assertEqual(mock_summary_instance.log_failure.call_count, 4)
        mock_summary_instance.log_failure.assert_any_call(
            "MR# MRN001 / Sample 1", "Failed to generate PDF: PDF Generation Failed"
        )

        # No files should be created because the mock always raises an exception
        self.assertEqual(len(os.listdir(self.output_dir)), 0)

    def test_organization_by_collection_date(self):
        """Test that PDFs are organized by collection date."""
        input_file = os.path.join(self.test_data_dir, "org_data.csv")
        # Using a fixed date format that the application expects for filenames
        with open(input_file, 'w') as f:
            f.write("Type,ID,Date collected,Name,MR#,Date of Birth,Collected by,Test completed,Test Name,Test result,Test units,Flags,Comment\n")
            f.write("Patient,1,2023-02-01,Patient A,MRN1,01/01/1990,Collector,2023-02-02 12:00,Test,Positive,,\n")
            f.write("Patient,2,2023-02-01,Patient B,MRN2,01/01/1990,Collector,2023-02-03 12:00,Test,Negative,,\n")
            f.write("Patient,3,2023-02-02,Patient C,MRN3,01/01/1990,Collector,2023-02-03 12:00,Test,Positive,,\n")

        try:
            main(input_file, self.output_dir, organize_by='collection-date')

            # Check for subdirectories
            self.assertTrue(os.path.isdir(os.path.join(self.output_dir, "2023-02-01")))
            self.assertTrue(os.path.isdir(os.path.join(self.output_dir, "2023-02-02")))

            # Check for files in subdirectories
            dir1_files = os.listdir(os.path.join(self.output_dir, "2023-02-01"))
            dir2_files = os.listdir(os.path.join(self.output_dir, "2023-02-02"))
            self.assertEqual(len(dir1_files), 2)
            self.assertEqual(len(dir2_files), 1)
            self.assertIn("Patient-A_MRN1_2023-02-01.pdf", dir1_files)
            self.assertIn("Patient-B_MRN2_2023-02-01.pdf", dir1_files)
            self.assertIn("Patient-C_MRN3_2023-02-02.pdf", dir2_files)
        finally:
            if os.path.exists(input_file):
                os.remove(input_file)

    def test_organization_by_tested_date(self):
        """Test that PDFs are organized by tested date."""
        input_file = os.path.join(self.test_data_dir, "org_data.csv")
        with open(input_file, 'w') as f:
            f.write("Type,ID,Date collected,Name,MR#,Date of Birth,Collected by,Test completed,Test Name,Test result,Test units,Flags,Comment\n")
            f.write("Patient,1,2023-02-01,Patient A,MRN1,01/01/1990,Collector,2023-02-02 12:00,Test,Positive,,\n")
            f.write("Patient,2,2023-02-01,Patient B,MRN2,01/01/1990,Collector,2023-02-03 12:00,Test,Negative,,\n")
            f.write("Patient,3,2023-02-02,Patient C,MRN3,01/01/1990,Collector,2023-02-03 12:00,Test,Positive,,\n")

        try:
            main(input_file, self.output_dir, organize_by='tested-date')

            self.assertTrue(os.path.isdir(os.path.join(self.output_dir, "2023-02-02")))
            self.assertTrue(os.path.isdir(os.path.join(self.output_dir, "2023-02-03")))

            dir1_files = os.listdir(os.path.join(self.output_dir, "2023-02-02"))
            dir2_files = os.listdir(os.path.join(self.output_dir, "2023-02-03"))
            self.assertEqual(len(dir1_files), 1)
            self.assertEqual(len(dir2_files), 2)
            self.assertIn("Patient-A_MRN1_2023-02-01.pdf", dir1_files)
            self.assertIn("Patient-B_MRN2_2023-02-01.pdf", dir2_files)
            self.assertIn("Patient-C_MRN3_2023-02-02.pdf", dir2_files)
        finally:
            if os.path.exists(input_file):
                os.remove(input_file)

    def test_organization_by_mrn(self):
        """Test that PDFs are organized by MRN."""
        input_file = os.path.join(self.test_data_dir, "org_data.csv")
        with open(input_file, 'w') as f:
            f.write("Type,ID,Date collected,Name,MR#,Date of Birth,Collected by,Test completed,Test Name,Test result,Test units,Flags,Comment\n")
            f.write("Patient,1,2023-02-01,Patient A,MRN1,01/01/1990,Collector,2023-02-02 12:00,Test,Positive,,\n")
            f.write("Patient,2,2023-02-01,Patient B,MRN2,01/01/1990,Collector,2023-02-03 12:00,Test,Negative,,\n")
            f.write("Patient,3,2023-02-02,Patient C,MRN3,01/01/1990,Collector,2023-02-03 12:00,Test,Positive,,\n")

        try:
            main(input_file, self.output_dir, organize_by='mrn')

            self.assertTrue(os.path.isdir(os.path.join(self.output_dir, "MRN_MRN1")))
            self.assertTrue(os.path.isdir(os.path.join(self.output_dir, "MRN_MRN2")))
            self.assertTrue(os.path.isdir(os.path.join(self.output_dir, "MRN_MRN3")))

            self.assertEqual(len(os.listdir(os.path.join(self.output_dir, "MRN_MRN1"))), 1)
            self.assertEqual(len(os.listdir(os.path.join(self.output_dir, "MRN_MRN2"))), 1)
            self.assertEqual(len(os.listdir(os.path.join(self.output_dir, "MRN_MRN3"))), 1)
        finally:
            if os.path.exists(input_file):
                os.remove(input_file)

    def test_positives_summary_pdf_generation(self):
        """Test that a summary PDF of positive results is created."""
        input_file = "tests/test_data/sample_data.csv"  # This file has positive results
        main(input_file, self.output_dir, organize_by=None)

        summary_pdf_path = os.path.join(self.output_dir, "positives_summary.pdf")
        self.assertTrue(os.path.exists(summary_pdf_path), "The positives summary PDF should be created.")

    def test_no_positives_summary_pdf_when_no_positives(self):
        """Test that a summary PDF is NOT created when there are no positive results."""
        input_file = os.path.join(self.test_data_dir, "negative_only_data.csv")
        with open(input_file, 'w') as f:
            f.write("Type,ID,Date collected,Name,MR#,Date of Birth,Collected by,Test completed,Test Name,Test result,Test units,Flags,Comment\n")
            f.write("Patient,1,2023-01-01,No Positives,MRN-NEG,01/01/1990,Collector,2023-01-01 12:00,Test,Negative,,\n")

        try:
            main(input_file, self.output_dir, organize_by=None)
            summary_pdf_path = os.path.join(self.output_dir, "positives_summary.pdf")
            self.assertFalse(os.path.exists(summary_pdf_path), "The positives summary PDF should NOT be created if there are no positives.")
        finally:
            if os.path.exists(input_file):
                os.remove(input_file)


    @patch('builtins.input', side_effect=KeyboardInterrupt)
    @patch('builtins.print')
    def test_cli_conflict_handler_keyboard_interrupt(self, mock_print, mock_input):
        """Test that a KeyboardInterrupt during conflict resolution is handled gracefully."""
        input_file = "tests/test_data/conflict_data.csv"
        main(input_file, self.output_dir, organize_by=None)

        # The conflict should be skipped, and a message printed
        mock_print.assert_any_call("\nOperation cancelled by user.")
        # Only the non-conflicting reports should be generated
        output_files = os.listdir(self.output_dir)
        self.assertNotIn("Conflict-Patient_MRN006_2023-01-20.pdf", output_files)
        # 2 reports, no summary pdf because positives were in the skipped sample
        self.assertEqual(len(output_files), 2)


    @patch('builtins.input', side_effect=EOFError)
    @patch('builtins.print')
    def test_cli_conflict_handler_eof_error(self, mock_print, mock_input):
        """Test that an EOFError during conflict resolution is handled gracefully."""
        input_file = "tests/test_data/conflict_data.csv"
        main(input_file, self.output_dir, organize_by=None)

        # The conflict should be skipped, and a message printed
        mock_print.assert_any_call("\nOperation cancelled by user.")
        # Only the non-conflicting reports should be generated
        output_files = os.listdir(self.output_dir)
        self.assertNotIn("Conflict-Patient_MRN006_2023-01-20.pdf", output_files)
        # 2 reports, no summary pdf because positives were in the skipped sample
        self.assertEqual(len(output_files), 2)


    def test_no_conflict_handler(self):
        """Test that the code proceeds without error if no conflict handler is provided."""
        input_file = "tests/test_data/conflict_data.csv"
        summary = RunSummary()
        # When no handler is provided, the conflicting sample is skipped.
        generate_reports(input_file, self.output_dir, None, summary, progress_callback=None, conflict_handler=None)
        # 2 reports + summary
        self.assertEqual(len(os.listdir(self.output_dir)), 3)

    @patch('main.RunSummary')
    def test_malformed_test_completed_date(self, mock_summary_class):
        """Test handling of a malformed 'Test completed' date."""
        mock_summary_instance = MagicMock()
        mock_summary_class.return_value = mock_summary_instance
        input_file = os.path.join(self.test_data_dir, "malformed_completed_date.csv")
        with open(input_file, 'w') as f:
            f.write("Type,ID,Date collected,Name,MR#,Date of Birth,Collected by,Test completed,Test Name,Test result,Test units,Flags,Comment\n")
            f.write("Patient,1,2023-01-01,Bad Date,MRN-BD,DOB,Collector,BAD-DATE,Test,Positive,ng/mL,,\n")

        try:
            main(input_file, self.output_dir, organize_by=None)
            # A report should still be generated with 'unknown-date' in the filename
            self.assertTrue(os.path.exists(os.path.join(self.output_dir, "Bad-Date_MRN-BD_2023-01-01.pdf")))
            mock_summary_instance.log_error.assert_called_once_with(
                "Patient MR# MRN-BD", "Could not parse 'Test completed' date ('BAD-DATE'). Error: Unknown datetime string format, unable to parse: BAD-DATE, at position 0"
            )
        finally:
            if os.path.exists(input_file):
                os.remove(input_file)

    @patch('main.generate_positives_summary_pdf', side_effect=Exception("Summary PDF Failed"))
    @patch('builtins.print')
    def test_positives_summary_pdf_generation_error(self, mock_print, mock_generate_summary):
        """Test that an error during summary PDF generation is caught and printed."""
        input_file = "tests/test_data/sample_data.csv"
        main(input_file, self.output_dir, organize_by=None)
        mock_print.assert_any_call("Error generating positives summary PDF: Summary PDF Failed")


if __name__ == '__main__':  # pragma: no cover
    unittest.main()