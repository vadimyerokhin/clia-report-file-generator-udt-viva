"""Comprehensive tests for the positive results summary PDF feature."""
import unittest
import os
import tempfile
import shutil
from src.run_summary import RunSummary
from src.pdf_generator import generate_positives_summary_pdf
from src.config import POSITIVES_SUMMARY_FILENAME
from PyPDF2 import PdfReader


class TestPositiveSummaryPDF(unittest.TestCase):
    """Test suite for positive results summary PDF generation."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.summary = RunSummary()
        self.summary.set_total_samples(10)

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_positive_summary_with_results(self):
        """Test normal case with multiple positive results."""
        # Add positive results (current API: mrn, patient_name, test_name, collection_date)
        self.summary.log_positive_result(
            "MRN123", "John Doe", "Opiates", "2024-01-15"
        )
        self.summary.log_positive_result(
            "MRN456", "Jane Smith", "Cocaine", "2024-01-16"
        )
        self.summary.log_positive_result(
            "MRN789", "Bob Johnson", "Amphetamines", "2024-01-17"
        )

        # Generate PDF (current API: summary, output_dir - no return value)
        generate_positives_summary_pdf(self.summary, self.test_dir)

        # Verify file was created with fixed filename
        output_path = os.path.join(self.test_dir, POSITIVES_SUMMARY_FILENAME)
        self.assertTrue(os.path.exists(output_path))

        # Verify PDF content
        reader = PdfReader(output_path)
        self.assertGreater(len(reader.pages), 0)

        # Extract text from first page
        page_text = reader.pages[0].extract_text()
        self.assertIn("John Doe", page_text)
        self.assertIn("Jane Smith", page_text)
        self.assertIn("Bob Johnson", page_text)
        self.assertIn("Opiates", page_text)
        self.assertIn("Cocaine", page_text)
        self.assertIn("Amphetamines", page_text)

    def test_positive_summary_no_results(self):
        """Test that no PDF is generated when there are no positive results."""
        # Don't add any positive results
        generate_positives_summary_pdf(self.summary, self.test_dir)

        # Verify file was NOT created (current behavior)
        output_path = os.path.join(self.test_dir, POSITIVES_SUMMARY_FILENAME)
        self.assertFalse(os.path.exists(output_path))

    def test_positive_summary_single_result(self):
        """Test edge case with single positive result."""
        self.summary.log_positive_result(
            "MRN001", "Single Patient", "Marijuana", "2024-01-20"
        )

        generate_positives_summary_pdf(self.summary, self.test_dir)

        output_path = os.path.join(self.test_dir, POSITIVES_SUMMARY_FILENAME)
        self.assertTrue(os.path.exists(output_path))

        reader = PdfReader(output_path)
        page_text = reader.pages[0].extract_text()
        self.assertIn("Single Patient", page_text)
        self.assertIn("Marijuana", page_text)

    def test_positive_summary_multiple_tests_same_patient(self):
        """Test patient with multiple positive tests on same date."""
        # Same patient, same date, multiple positive tests
        self.summary.log_positive_result(
            "MRN999", "Multi Test", "Opiates", "2024-01-25"
        )
        self.summary.log_positive_result(
            "MRN999", "Multi Test", "Cocaine", "2024-01-25"
        )
        self.summary.log_positive_result(
            "MRN999", "Multi Test", "Marijuana", "2024-01-25"
        )

        generate_positives_summary_pdf(self.summary, self.test_dir)

        output_path = os.path.join(self.test_dir, POSITIVES_SUMMARY_FILENAME)
        self.assertTrue(os.path.exists(output_path))

        reader = PdfReader(output_path)
        page_text = reader.pages[0].extract_text()

        # Should show all tests
        self.assertIn("Multi Test", page_text)
        self.assertIn("Opiates", page_text)
        self.assertIn("Cocaine", page_text)
        self.assertIn("Marijuana", page_text)

    def test_positive_summary_missing_collection_date(self):
        """Test handling of missing collection date field."""
        self.summary.log_positive_result(
            "MRN111", "No Date Patient", "Opiates", ""
        )

        generate_positives_summary_pdf(self.summary, self.test_dir)

        output_path = os.path.join(self.test_dir, POSITIVES_SUMMARY_FILENAME)
        self.assertTrue(os.path.exists(output_path))

        reader = PdfReader(output_path)
        page_text = reader.pages[0].extract_text()
        self.assertIn("No Date Patient", page_text)

    def test_positive_summary_fixed_filename(self):
        """Test that filename is the fixed positives_summary.pdf."""
        self.summary.log_positive_result(
            "MRN333", "Test Patient", "Opiates", "2024-02-01"
        )

        generate_positives_summary_pdf(self.summary, self.test_dir)

        # Check that the fixed filename is used
        output_path = os.path.join(self.test_dir, POSITIVES_SUMMARY_FILENAME)
        self.assertTrue(os.path.exists(output_path))
        self.assertEqual(os.path.basename(output_path), "positives_summary.pdf")

    def test_positive_summary_output_location(self):
        """Test that summary is saved to main output directory."""
        # Create subdirectory structure
        sub_dir = os.path.join(self.test_dir, "2024-01-15")
        os.makedirs(sub_dir)

        self.summary.log_positive_result(
            "MRN444", "Location Test", "Opiates", "2024-01-15"
        )

        # Generate PDF in main directory
        generate_positives_summary_pdf(self.summary, self.test_dir)

        # Verify saved to main directory, NOT subdirectory
        output_path = os.path.join(self.test_dir, POSITIVES_SUMMARY_FILENAME)
        self.assertTrue(os.path.exists(output_path))
        self.assertEqual(os.path.dirname(output_path), self.test_dir)

    def test_positive_summary_with_organized_output(self):
        """Test that summary works correctly even with organize-by subdirectories."""
        # Create organization subdirectories
        os.makedirs(os.path.join(self.test_dir, "MRN_123"))
        os.makedirs(os.path.join(self.test_dir, "MRN_456"))

        self.summary.log_positive_result(
            "MRN123", "Organized Patient 1", "Opiates", "2024-01-20"
        )
        self.summary.log_positive_result(
            "MRN456", "Organized Patient 2", "Cocaine", "2024-01-21"
        )

        generate_positives_summary_pdf(self.summary, self.test_dir)

        # Should still be in root directory
        output_path = os.path.join(self.test_dir, POSITIVES_SUMMARY_FILENAME)
        self.assertTrue(os.path.exists(output_path))
        self.assertEqual(os.path.dirname(output_path), self.test_dir)

        # Verify content includes both patients
        reader = PdfReader(output_path)
        page_text = reader.pages[0].extract_text()
        self.assertIn("Organized Patient 1", page_text)
        self.assertIn("Organized Patient 2", page_text)

    def test_positive_summary_large_dataset(self):
        """Test handling of large number of positive results."""
        # Add many positive results
        for i in range(50):
            self.summary.log_positive_result(
                f"MRN{i:03d}", f"Patient {i}", f"Test {i % 5}", "2024-01-15"
            )

        generate_positives_summary_pdf(self.summary, self.test_dir)

        output_path = os.path.join(self.test_dir, POSITIVES_SUMMARY_FILENAME)
        self.assertTrue(os.path.exists(output_path))

        # Verify PDF was created successfully
        reader = PdfReader(output_path)
        self.assertGreater(len(reader.pages), 0)

        # Check that summary statistics are correct
        page_text = reader.pages[0].extract_text()
        self.assertIn("50", page_text)  # Should mention count of results

    def test_positive_summary_error_handling(self):
        """Test error handling for invalid output directory."""
        self.summary.log_positive_result(
            "MRN666", "Error Test", "Opiates", "2024-02-10"
        )

        # Try to write to non-existent directory with no permission
        invalid_dir = "/invalid/nonexistent/path"

        with self.assertRaises(Exception):
            generate_positives_summary_pdf(self.summary, invalid_dir)


if __name__ == '__main__':
    unittest.main()
