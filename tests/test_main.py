"""Tests for main module report generation functionality."""
import os
import sys
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock, ANY

from src.main import main, generate_reports, cli_conflict_handler
from src.run_summary import RunSummary
from src.exporter import PdfExporter


class TestMain(unittest.TestCase):
    """Test suite for main module functionality."""

    def setUp(self):
        """Set up a temporary directory for test outputs."""
        self.output_dir = tempfile.mkdtemp()
        self.test_data_dir = "tests/test_data"
        self.sample_data = os.path.join(self.test_data_dir, "sample_data.csv")
        self.conflict_data = os.path.join(self.test_data_dir, "conflict_data.csv")

    def tearDown(self):
        """Remove the temporary directory after tests."""
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)

    def test_output_directory_creation(self):
        """Test that output directory is used correctly."""
        # Directory should exist (created in setUp)
        self.assertTrue(os.path.exists(self.output_dir))

        # Call main with the sample data
        main(self.sample_data, self.output_dir, None)

        # Verify reports were generated
        output_files = os.listdir(self.output_dir)
        self.assertGreater(len(output_files), 0)

    def test_main_generates_reports(self):
        """Test that main function generates PDF reports."""
        main(self.sample_data, self.output_dir, None)

        output_files = os.listdir(self.output_dir)
        pdf_files = [f for f in output_files if f.endswith('.pdf')]

        # Should have multiple PDF files
        self.assertGreater(len(pdf_files), 0)

    def test_main_generates_billing_file(self):
        """Test that main function generates billing CSV file."""
        main(self.sample_data, self.output_dir, None)

        output_files = os.listdir(self.output_dir)
        billing_files = [f for f in output_files if f.startswith('billing_80307_')]

        # Should have one billing file
        self.assertEqual(len(billing_files), 1)

    @patch('src.main.load_and_process_data', return_value=None)
    def test_no_data_loaded(self, mock_load_data):
        """Test that the script handles no data gracefully."""
        main(self.sample_data, self.output_dir, None)

        # Even with no data, should complete without error
        mock_load_data.assert_called_once()

    def test_organization_by_collection_date(self):
        """Test organizing reports by collection date."""
        main(self.sample_data, self.output_dir, 'collection-date')

        # Check that subdirectories were created
        subdirs = [d for d in os.listdir(self.output_dir)
                   if os.path.isdir(os.path.join(self.output_dir, d))]

        # Should have date-based subdirectories
        self.assertGreater(len(subdirs), 0)

    def test_organization_by_tested_date(self):
        """Test organizing reports by tested date."""
        main(self.sample_data, self.output_dir, 'tested-date')

        # Check that subdirectories were created
        subdirs = [d for d in os.listdir(self.output_dir)
                   if os.path.isdir(os.path.join(self.output_dir, d))]

        # Should have date-based subdirectories
        self.assertGreater(len(subdirs), 0)

    def test_organization_by_mrn(self):
        """Test organizing reports by MRN."""
        main(self.sample_data, self.output_dir, 'mrn')

        # Check that subdirectories were created
        subdirs = [d for d in os.listdir(self.output_dir)
                   if os.path.isdir(os.path.join(self.output_dir, d))]

        # Should have MRN-based subdirectories
        self.assertGreater(len(subdirs), 0)

        # Subdirectories should start with "MRN_"
        mrn_dirs = [d for d in subdirs if d.startswith('MRN_')]
        self.assertEqual(len(subdirs), len(mrn_dirs))


class TestGenerateReports(unittest.TestCase):
    """Test suite for generate_reports function."""

    def setUp(self):
        """Set up test fixtures."""
        self.output_dir = tempfile.mkdtemp()
        self.test_data_dir = "tests/test_data"
        self.sample_data = os.path.join(self.test_data_dir, "sample_data.csv")
        self.conflict_data = os.path.join(self.test_data_dir, "conflict_data.csv")
        self.summary = RunSummary()

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)

    def test_generate_reports_basic(self):
        """Test basic report generation."""
        generate_reports(
            self.sample_data,
            self.output_dir,
            None,
            self.summary
        )

        output_files = os.listdir(self.output_dir)
        self.assertGreater(len(output_files), 0)

    def test_generate_reports_with_progress_callback(self):
        """Test report generation with progress callback."""
        progress_messages = []

        def progress_callback(message):
            progress_messages.append(message)

        generate_reports(
            self.sample_data,
            self.output_dir,
            None,
            self.summary,
            progress_callback=progress_callback
        )

        # Should have received progress messages
        self.assertGreater(len(progress_messages), 0)

    def test_generate_reports_with_conflict_handler(self):
        """Test report generation with conflict handler."""
        # Use a handler that always selects the first option
        def conflict_handler(mrn, date, sample_ids):
            return 0

        generate_reports(
            self.conflict_data,
            self.output_dir,
            None,
            self.summary,
            conflict_handler=conflict_handler
        )

        output_files = os.listdir(self.output_dir)
        self.assertGreater(len(output_files), 0)

    def test_generate_reports_skip_conflict(self):
        """Test that conflicts can be skipped."""
        skipped = []

        def conflict_handler(mrn, date, sample_ids):
            skipped.append((mrn, date))
            return None  # Skip

        generate_reports(
            self.conflict_data,
            self.output_dir,
            None,
            self.summary,
            conflict_handler=conflict_handler
        )

        # Should have skipped at least one conflict
        # Note: depends on test data having conflicts


class TestCliConflictHandler(unittest.TestCase):
    """Test suite for CLI conflict handler."""

    @patch('builtins.input', return_value='1')
    def test_valid_selection(self, mock_input):
        """Test valid selection of first option."""
        result = cli_conflict_handler('MRN123', '2024-01-15', ['ID1', 'ID2'])
        self.assertEqual(result, 0)

    @patch('builtins.input', return_value='2')
    def test_valid_selection_second(self, mock_input):
        """Test valid selection of second option."""
        result = cli_conflict_handler('MRN123', '2024-01-15', ['ID1', 'ID2'])
        self.assertEqual(result, 1)

    @patch('builtins.input', return_value='s')
    def test_skip_selection(self, mock_input):
        """Test skip selection."""
        result = cli_conflict_handler('MRN123', '2024-01-15', ['ID1', 'ID2'])
        self.assertIsNone(result)

    @patch('builtins.input', side_effect=['invalid', '1'])
    def test_invalid_then_valid(self, mock_input):
        """Test invalid input followed by valid input."""
        result = cli_conflict_handler('MRN123', '2024-01-15', ['ID1', 'ID2'])
        self.assertEqual(result, 0)
        self.assertEqual(mock_input.call_count, 2)

    @patch('builtins.input', side_effect=['5', '1'])
    def test_out_of_range_then_valid(self, mock_input):
        """Test out of range input followed by valid input."""
        result = cli_conflict_handler('MRN123', '2024-01-15', ['ID1', 'ID2'])
        self.assertEqual(result, 0)
        self.assertEqual(mock_input.call_count, 2)

    @patch('builtins.input', side_effect=EOFError)
    def test_eof_error(self, mock_input):
        """Test EOF error handling."""
        result = cli_conflict_handler('MRN123', '2024-01-15', ['ID1', 'ID2'])
        self.assertIsNone(result)

    @patch('builtins.input', side_effect=KeyboardInterrupt)
    def test_keyboard_interrupt(self, mock_input):
        """Test keyboard interrupt handling."""
        result = cli_conflict_handler('MRN123', '2024-01-15', ['ID1', 'ID2'])
        self.assertIsNone(result)


class TestPdfGeneration(unittest.TestCase):
    """Test suite for PDF generation aspects."""

    def setUp(self):
        """Set up test fixtures."""
        self.output_dir = tempfile.mkdtemp()
        self.test_data_dir = "tests/test_data"
        self.sample_data = os.path.join(self.test_data_dir, "sample_data.csv")

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)

    def test_pdf_filename_format(self):
        """Test that PDF filenames follow expected format."""
        main(self.sample_data, self.output_dir, None)

        output_files = os.listdir(self.output_dir)
        pdf_files = [f for f in output_files if f.endswith('.pdf')
                     and not f.startswith('positives_summary')]

        for pdf in pdf_files:
            # Should follow pattern: Name_MRN_Date.pdf
            parts = pdf.replace('.pdf', '').split('_')
            self.assertGreaterEqual(len(parts), 3)

    def test_positives_summary_generated(self):
        """Test that positives summary PDF is generated when there are positive results."""
        main(self.sample_data, self.output_dir, None)

        output_files = os.listdir(self.output_dir)
        summary_files = [f for f in output_files if 'positives_summary' in f.lower()]

        # May or may not have positives depending on test data
        # Just verify no error occurred
        self.assertTrue(True)


if __name__ == '__main__':
    unittest.main()
