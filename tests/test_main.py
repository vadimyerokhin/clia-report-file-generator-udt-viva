import os
import sys
import shutil
import unittest
from unittest.mock import patch, MagicMock, ANY

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from main import main, generate_reports
from src.run_summary import RunSummary
from src.exporter import PdfExporter

class TestMain(unittest.TestCase):

    def setUp(self):
        """Set up a temporary directory for test outputs."""
        self.output_dir = "temp_test_output"
        self.test_data_dir = "tests/test_data"
        self.config_file = "config.yaml"

        # Ensure the directories are clean before each test
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
        if not os.path.exists(self.test_data_dir):
            os.makedirs(self.test_data_dir)

        # Create a dummy config file for testing
        with open(self.config_file, 'w') as f:
            f.write(f"input_file: tests/test_data/sample_data.csv\n")
            f.write(f"output_dir: {self.output_dir}\n")

    def tearDown(self):
        """Remove the temporary directory and config file after tests."""
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
        if os.path.exists(self.config_file):
            os.remove(self.config_file)

    @patch('builtins.input', side_effect=['2'])  # Simulate user choosing the second option
    def test_conflict_resolution_flow(self, mock_input):
        """Test the full flow with a data file containing a conflict."""
        with open(self.config_file, 'w') as f:
            f.write(f"input_file: tests/test_data/conflict_data.csv\n")
            f.write(f"output_dir: {self.output_dir}\n")
        main(argv=[])

        # Check that only one report was generated for the conflict patient
        expected_filename = "Conflict-Patient_MRN006_2023-01-20.pdf"
        output_files = os.listdir(self.output_dir)

        # There should be 5 files in total: one for MRN001, one for MRN002, one for MRN006, positive summary with timestamp, and billing file
        self.assertEqual(len(output_files), 5, "Should generate five files in total.")

        # Check that the specific, user-selected report exists
        self.assertIn(expected_filename, output_files, "The PDF for the selected conflicted sample should be generated.")
        # Check for positive summary with timestamp
        positive_summaries = [f for f in output_files if f.startswith("Positive_Results_Summary_")]
        self.assertEqual(len(positive_summaries), 1, "Should have one positive results summary PDF")

    def test_output_directory_creation(self):
        """Test that the output directory is created if it does not exist."""
        self.assertFalse(os.path.exists(self.output_dir))
        main(argv=[])
        self.assertTrue(os.path.exists(self.output_dir))

    @patch('main.load_and_process_data', return_value=None)
    def test_no_data_loaded(self, mock_load_data):
        """Test that the script exits gracefully if no data is loaded."""
        main(argv=[])
        self.assertTrue(os.path.exists(self.output_dir))
        # Even with no data, positive summary is still generated (with "no positives" message)
        output_files = os.listdir(self.output_dir)
        self.assertEqual(len(output_files), 1, "Only positive summary should be generated when no data is loaded")
        positive_summaries = [f for f in output_files if f.startswith("Positive_Results_Summary_")]
        self.assertEqual(len(positive_summaries), 1, "Should have positive summary with 'no results' message")
        mock_load_data.assert_called_with("tests/test_data/sample_data.csv", ANY)

    @patch('builtins.input', side_effect=['a', '3', '1'])  # Invalid, out of range, then valid
    def test_invalid_user_input_for_conflict(self, mock_input):
        """Test handling of invalid and out-of-range user input."""
        with open(self.config_file, 'w') as f:
            f.write(f"input_file: tests/test_data/conflict_data.csv\n")
            f.write(f"output_dir: {self.output_dir}\n")
        main(argv=[])
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

        with open(self.config_file, 'w') as f:
            f.write(f"input_file: tests/test_data/conflict_data.csv\n")
            f.write(f"output_dir: {self.output_dir}\n")
        main(argv=[])

        # The conflict patient should be skipped, but summary and billing file are still generated
        output_files = os.listdir(self.output_dir)
        self.assertEqual(len(output_files), 4)  # 2 PDFs + summary + billing
        self.assertNotIn("Conflict-Patient_MRN006_2023-01-20.pdf", output_files)

        # Check that the skip was logged
        mock_summary_instance.log_user_skip.assert_called_once_with('MRN006', '2023-01-20', ANY)

    @patch('main.RunSummary')
    def test_malformed_date_handling(self, mock_summary_class):
        """Test that a malformed date does not crash the application and is logged."""
        mock_summary_instance = MagicMock()
        mock_summary_instance._positive_results = []
        mock_summary_instance.positive_results = []
        mock_summary_class.return_value = mock_summary_instance

        malformed_date_file = os.path.join(self.test_data_dir, "malformed_date_data.csv")
        with open(malformed_date_file, 'w') as f:
            f.write("Type,ID,Date collected,Name,MR#,Date of Birth,Collected by,Test completed,Test Name,Test result,Test units,Flags,Comment\n")
            f.write("Patient,1,NOT-A-DATE,Bad Date Patient,MRN-DATE,01/01/1990,Collector,01/15/2023 12:00:00 PM,Test,Positive,ng/mL,,\n")

        with open(self.config_file, 'w') as f:
            f.write(f"input_file: {malformed_date_file}\n")
            f.write(f"output_dir: {self.output_dir}\n")

        try:
            main(argv=[])
            # Billing file and positive summary should be created (no patient PDFs due to malformed date)
            output_files = os.listdir(self.output_dir)
            self.assertEqual(len(output_files), 2, "Should have billing file and positive summary")
            # Verify it's the billing file
            files = os.listdir(self.output_dir)
            self.assertTrue(any(f.startswith('billing_80307_') for f in files))
            # The error should be logged
            mock_summary_instance.log_failure.assert_called_once_with(
                "MR# MRN-DATE", "The date 'NOT-A-DATE' in the 'Date collected' column could not be parsed."
            )
        finally:
            if os.path.exists(malformed_date_file):
                os.remove(malformed_date_file)

    @patch('main.RunSummary')
    @patch('exporter.PdfExporter.export_report', side_effect=Exception("PDF Generation Failed"))
    def test_pdf_generation_error_handling(self, mock_generate_pdf, mock_summary_class):
        """Test that an error during PDF generation is caught and logged."""
        mock_summary_instance = MagicMock()
        mock_summary_instance._positive_results = []
        mock_summary_instance.positive_results = []
        mock_summary_class.return_value = mock_summary_instance

        main(argv=[])

        # The error should be logged for each of the 4 samples
        self.assertEqual(mock_summary_instance.log_failure.call_count, 4)
        mock_summary_instance.log_failure.assert_any_call(
            "MR# MRN001 / Sample 1", "Failed to generate PDF: PDF Generation Failed"
        )

        # Only billing file and positive summary should be created (no patient PDFs because the mock always raises an exception)
        output_files = os.listdir(self.output_dir)
        self.assertEqual(len(output_files), 2, "Should have billing file and positive summary")
        billing_files = [f for f in output_files if f.startswith("billing_")]
        positive_summaries = [f for f in output_files if f.startswith("Positive_Results_Summary_")]
        self.assertEqual(len(billing_files), 1, "Should have one billing file")
        self.assertEqual(len(positive_summaries), 1, "Should have one positive summary")
        files = os.listdir(self.output_dir)
        self.assertTrue(any(f.startswith('billing_80307_') for f in files))

    def test_organization_by_collection_date(self):
        """Test that PDFs are organized by collection date."""
        input_file = os.path.join(self.test_data_dir, "org_data.csv")
        # Using a fixed date format that the application expects for filenames
        with open(input_file, 'w') as f:
            f.write("Type,ID,Date collected,Name,MR#,Date of Birth,Collected by,Test completed,Test Name,Test result,Test units,Flags,Comment\n")
            f.write("Patient,1,2023-02-01,Patient A,MRN1,01/01/1990,Collector,2023-02-02 12:00,Test,Positive, ,\n")
            f.write("Patient,2,2023-02-01,Patient B,MRN2,01/01/1990,Collector,2023-02-03 12:00,Test,Negative, ,\n")
            f.write("Patient,3,2023-02-02,Patient C,MRN3,01/01/1990,Collector,2023-02-03 12:00,Test,Positive, ,\n")

        with open(self.config_file, 'w') as f:
            f.write(f"input_file: {input_file}\n")
            f.write(f"output_dir: {self.output_dir}\n")
            f.write(f"organize_by: collection-date\n")

        try:
            main(argv=[])

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
            f.write("Patient,1,2023-02-01,Patient A,MRN1,01/01/1990,Collector,2023-02-02 12:00,Test,Positive, ,\n")
            f.write("Patient,2,2023-02-01,Patient B,MRN2,01/01/1990,Collector,2023-02-03 12:00,Test,Negative, ,\n")
            f.write("Patient,3,2023-02-02,Patient C,MRN3,01/01/1990,Collector,2023-02-03 12:00,Test,Positive, ,\n")

        with open(self.config_file, 'w') as f:
            f.write(f"input_file: {input_file}\n")
            f.write(f"output_dir: {self.output_dir}\n")
            f.write(f"organize_by: tested-date\n")

        try:
            main(argv=[])

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
            f.write("Patient,1,2023-02-01,Patient A,MRN1,01/01/1990,Collector,2023-02-02 12:00,Test,Positive, ,\n")
            f.write("Patient,2,2023-02-01,Patient B,MRN2,01/01/1990,Collector,2023-02-03 12:00,Test,Negative, ,\n")
            f.write("Patient,3,2023-02-02,Patient C,MRN3,01/01/1990,Collector,2023-02-03 12:00,Test,Positive, ,\n")

        with open(self.config_file, 'w') as f:
            f.write(f"input_file: {input_file}\n")
            f.write(f"output_dir: {self.output_dir}\n")
            f.write(f"organize_by: mrn\n")

        try:
            main(argv=[])

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
        main(argv=[])

        # Check for timestamped summary PDF
        output_files = os.listdir(self.output_dir)
        positive_summaries = [f for f in output_files if f.startswith("Positive_Results_Summary_")]
        self.assertEqual(len(positive_summaries), 1, "Exactly one positive results summary PDF should be created.")
        self.assertTrue(positive_summaries[0].endswith(".pdf"), "Summary file should be a PDF.")

    def test_no_positives_summary_pdf_when_no_positives(self):
        """Test that a summary PDF with 'no positive results' message is created."""
        input_file = os.path.join(self.test_data_dir, "negative_only_data.csv")
        with open(input_file, 'w') as f:
            f.write("Type,ID,Date collected,Name,MR#,Date of Birth,Collected by,Test completed,Test Name,Test result,Test units,Flags,Comment\n")
            f.write("Patient,1,2023-01-01,No Positives,MRN-NEG,01/01/1990,Collector,2023-01-01 12:00,Test,Negative, ,\n")

        with open(self.config_file, 'w') as f:
            f.write(f"input_file: {input_file}\n")
            f.write(f"output_dir: {self.output_dir}\n")

        try:
            main(argv=[])
            # Now a summary PDF IS created even with no positives (with informational message)
            output_files = os.listdir(self.output_dir)
            positive_summaries = [f for f in output_files if f.startswith("Positive_Results_Summary_")]
            self.assertEqual(len(positive_summaries), 1, "A summary PDF should be created even with no positives.")
        finally:
            if os.path.exists(input_file):
                os.remove(input_file)


    @patch('builtins.input', side_effect=KeyboardInterrupt)
    @patch('builtins.print')
    def test_cli_conflict_handler_keyboard_interrupt(self, mock_print, mock_input):
        """Test that a KeyboardInterrupt during conflict resolution is handled gracefully."""
        with open(self.config_file, 'w') as f:
            f.write(f"input_file: tests/test_data/conflict_data.csv\n")
            f.write(f"output_dir: {self.output_dir}\n")
        main(argv=[])

        # The conflict should be skipped, and a message printed
        mock_print.assert_any_call("\nOperation cancelled by user.")
        # Only the non-conflicting reports should be generated
        output_files = os.listdir(self.output_dir)
        self.assertNotIn("Conflict-Patient_MRN006_2023-01-20.pdf", output_files)
        # 2 PDFs + billing file (no summary pdf because positives were in the skipped sample)
        self.assertEqual(len(output_files), 4)


    @patch('builtins.input', side_effect=EOFError)
    @patch('builtins.print')
    def test_cli_conflict_handler_eof_error(self, mock_print, mock_input):
        """Test that an EOFError during conflict resolution is handled gracefully."""
        with open(self.config_file, 'w') as f:
            f.write(f"input_file: tests/test_data/conflict_data.csv\n")
            f.write(f"output_dir: {self.output_dir}\n")
        main(argv=[])

        # The conflict should be skipped, and a message printed
        mock_print.assert_any_call("\nOperation cancelled by user.")
        # Only the non-conflicting reports should be generated
        output_files = os.listdir(self.output_dir)
        self.assertNotIn("Conflict-Patient_MRN006_2023-01-20.pdf", output_files)
        # 2 PDFs + billing file (no summary pdf because positives were in the skipped sample)
        self.assertEqual(len(output_files), 4)


    def test_no_conflict_handler(self):
        """Test that the code proceeds without error if no conflict handler is provided."""
        input_file = "tests/test_data/conflict_data.csv"
        summary = RunSummary()
        exporter = PdfExporter()
        # When no handler is provided, the conflicting sample is skipped.
        generate_reports(input_file, self.output_dir, None, summary, exporter, progress_callback=None, conflict_handler=None)
        # 2 PDFs + summary + billing file
        self.assertEqual(len(os.listdir(self.output_dir)), 4)

    @patch('main.RunSummary')
    def test_malformed_test_completed_date(self, mock_summary_class):
        """Test handling of a malformed 'Test completed' date."""
        mock_summary_instance = MagicMock()
        mock_summary_class.return_value = mock_summary_instance
        input_file = os.path.join(self.test_data_dir, "malformed_completed_date.csv")
        with open(input_file, 'w') as f:
            f.write("Type,ID,Date collected,Name,MR#,Date of Birth,Collected by,Test completed,Test Name,Test result,Test units,Flags,Comment\n")
            f.write("Patient,1,2023-01-01,Bad Date,MRN-BD,DOB,Collector,BAD-DATE,Test,Positive,ng/mL, ,\n")

        with open(self.config_file, 'w') as f:
            f.write(f"input_file: {input_file}\n")
            f.write(f"output_dir: {self.output_dir}\n")

        try:
            main(argv=[])
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
        main(argv=[])
        mock_print.assert_any_call("Error generating positive results summary PDF: Summary PDF Failed")


if __name__ == '__main__':  # pragma: no cover
    unittest.main()
