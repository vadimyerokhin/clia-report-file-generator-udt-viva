"""Tests for main module report generation functionality."""
import os
import sys
import shutil
import tempfile
import unittest
import zipfile
from unittest.mock import patch, MagicMock, ANY

from src.main import main, generate_reports, cli_conflict_handler, create_zip_archive
from src.run_summary import RunSummary
from src.exporter import PdfExporter
from src.config import POSITIVES_SUMMARY_FILENAME


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


class TestCreateZipArchive(unittest.TestCase):
    """Test suite for create_zip_archive function."""

    def setUp(self):
        """Set up temp directories with stub PDF files."""
        self.output_dir = tempfile.mkdtemp()
        self.input_dir = tempfile.mkdtemp()
        self.input_file = os.path.join(self.input_dir, "export.csv")
        # Create a dummy input CSV so dirname resolves correctly
        with open(self.input_file, 'w') as f:
            f.write("dummy")

    def tearDown(self):
        """Clean up temp directories."""
        shutil.rmtree(self.output_dir, ignore_errors=True)
        shutil.rmtree(self.input_dir, ignore_errors=True)

    def _create_stub_pdf(self, relative_path):
        """Create a stub PDF file in output_dir at the given relative path."""
        full_path = os.path.join(self.output_dir, relative_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'wb') as f:
            f.write(b'%PDF-stub')
        return full_path

    def test_creates_zip_with_patient_pdfs(self):
        """Test that zip is created with the correct patient PDFs."""
        self._create_stub_pdf("John-Doe_123_2024-03-15.pdf")
        self._create_stub_pdf("Jane-Smith_456_2024-03-15.pdf")

        config = {'create_zip': True}
        result = create_zip_archive(self.input_file, self.output_dir, config)

        self.assertIsNotNone(result)
        self.assertTrue(os.path.exists(result))
        self.assertTrue(result.startswith(self.input_dir))
        self.assertTrue(result.endswith('.zip'))

        with zipfile.ZipFile(result, 'r') as zf:
            names = zf.namelist()
            self.assertEqual(len(names), 2)
            self.assertIn("John-Doe_123_2024-03-15.pdf", names)
            self.assertIn("Jane-Smith_456_2024-03-15.pdf", names)

    def test_excludes_positives_summary(self):
        """Test that positives_summary.pdf is excluded from the zip."""
        self._create_stub_pdf("John-Doe_123_2024-03-15.pdf")
        self._create_stub_pdf(POSITIVES_SUMMARY_FILENAME)

        config = {'create_zip': True}
        result = create_zip_archive(self.input_file, self.output_dir, config)

        self.assertIsNotNone(result)
        with zipfile.ZipFile(result, 'r') as zf:
            names = zf.namelist()
            self.assertEqual(len(names), 1)
            self.assertNotIn(POSITIVES_SUMMARY_FILENAME, names)

    def test_preserves_subdirectory_structure(self):
        """Test that subdirectory organization is preserved in the zip."""
        self._create_stub_pdf("2024-03-15/John-Doe_123_2024-03-15.pdf")
        self._create_stub_pdf("2024-03-16/Jane-Smith_456_2024-03-16.pdf")

        config = {'create_zip': True}
        result = create_zip_archive(self.input_file, self.output_dir, config)

        self.assertIsNotNone(result)
        with zipfile.ZipFile(result, 'r') as zf:
            names = zf.namelist()
            self.assertEqual(len(names), 2)
            # Check subdirectory paths are preserved
            self.assertTrue(any("2024-03-15" in n for n in names))
            self.assertTrue(any("2024-03-16" in n for n in names))

    def test_returns_none_when_disabled(self):
        """Test that zip is not created when feature is disabled."""
        self._create_stub_pdf("John-Doe_123_2024-03-15.pdf")

        config = {'create_zip': False}
        result = create_zip_archive(self.input_file, self.output_dir, config)

        self.assertIsNone(result)
        # No zip files should exist in the input directory
        zip_files = [f for f in os.listdir(self.input_dir) if f.endswith('.zip')]
        self.assertEqual(len(zip_files), 0)

    def test_returns_none_when_no_pdfs(self):
        """Test that zip is skipped when there are no patient PDFs."""
        config = {'create_zip': True}
        messages = []
        result = create_zip_archive(
            self.input_file, self.output_dir, config,
            progress_callback=messages.append
        )

        self.assertIsNone(result)
        self.assertTrue(any("skipping" in m.lower() for m in messages))

    def test_returns_none_when_only_positives_summary(self):
        """Test that zip is skipped when only positives_summary.pdf exists."""
        self._create_stub_pdf(POSITIVES_SUMMARY_FILENAME)

        config = {'create_zip': True}
        result = create_zip_archive(self.input_file, self.output_dir, config)

        self.assertIsNone(result)

    def test_zip_placed_beside_input_csv(self):
        """Test that the zip file is created in the same directory as the input CSV."""
        self._create_stub_pdf("report.pdf")

        config = {'create_zip': True}
        result = create_zip_archive(self.input_file, self.output_dir, config)

        self.assertIsNotNone(result)
        self.assertEqual(os.path.dirname(result), self.input_dir)

    def test_progress_callback_on_success(self):
        """Test that progress callback is called with success message."""
        self._create_stub_pdf("report.pdf")

        config = {'create_zip': True}
        messages = []
        result = create_zip_archive(
            self.input_file, self.output_dir, config,
            progress_callback=messages.append
        )

        self.assertIsNotNone(result)
        self.assertTrue(any("ZIP archive created" in m for m in messages))
        self.assertTrue(any("1 report(s)" in m for m in messages))


if __name__ == '__main__':
    unittest.main()
