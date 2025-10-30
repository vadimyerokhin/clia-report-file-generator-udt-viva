"""Comprehensive tests for the positive results summary PDF feature."""
import unittest
import os
import tempfile
import shutil
from datetime import datetime
from src.run_summary import RunSummary
from src.pdf_generator import generate_positives_summary_pdf
from reportlab.pdfgen import canvas
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
        # Add positive results
        self.summary.log_positive_result(
            "MRN123", "John Doe", "Opiates", "2024-01-15",
            "1985-05-10", "01/16/2024"
        )
        self.summary.log_positive_result(
            "MRN456", "Jane Smith", "Cocaine", "2024-01-16",
            "1990-08-22", "01/17/2024"
        )
        self.summary.log_positive_result(
            "MRN789", "Bob Johnson", "Amphetamines", "2024-01-17",
            "1978-12-03", "01/18/2024"
        )

        # Generate PDF
        output_path = generate_positives_summary_pdf(self.summary, self.test_dir, 10)

        # Verify file was created
        self.assertTrue(os.path.exists(output_path))

        # Verify filename format (timestamped)
        filename = os.path.basename(output_path)
        self.assertTrue(filename.startswith("Positive_Results_Summary_"))
        self.assertTrue(filename.endswith(".pdf"))

        # Verify PDF content
        reader = PdfReader(output_path)
        self.assertGreater(len(reader.pages), 0)

        # Extract text from first page
        page_text = reader.pages[0].extract_text()
        self.assertIn("positive results summary report", page_text.lower())
        self.assertIn("John Doe", page_text)
        self.assertIn("Jane Smith", page_text)
        self.assertIn("Bob Johnson", page_text)
        self.assertIn("Opiates", page_text)
        self.assertIn("Cocaine", page_text)
        self.assertIn("Amphetamines", page_text)

    def test_positive_summary_no_results(self):
        """Test generation of informational PDF when no positive results."""
        # Don't add any positive results
        output_path = generate_positives_summary_pdf(self.summary, self.test_dir, 10)

        # Verify file was created
        self.assertTrue(os.path.exists(output_path))

        # Verify PDF content shows "no positive results"
        reader = PdfReader(output_path)
        page_text = reader.pages[0].extract_text()
        self.assertIn("No positive results detected", page_text)
        self.assertIn("Total Samples Processed: 10", page_text)

    def test_positive_summary_single_result(self):
        """Test edge case with single positive result."""
        self.summary.log_positive_result(
            "MRN001", "Single Patient", "Marijuana", "2024-01-20",
            "1995-03-15", "01/21/2024"
        )

        output_path = generate_positives_summary_pdf(self.summary, self.test_dir, 5)
        self.assertTrue(os.path.exists(output_path))

        reader = PdfReader(output_path)
        page_text = reader.pages[0].extract_text()
        self.assertIn("Single Patient", page_text)
        self.assertIn("Marijuana", page_text)

    def test_positive_summary_multiple_tests_same_patient(self):
        """Test grouping: patient with multiple positive tests on same date."""
        # Same patient, same date, multiple positive tests
        self.summary.log_positive_result(
            "MRN999", "Multi Test", "Opiates", "2024-01-25",
            "1980-01-01", "01/26/2024"
        )
        self.summary.log_positive_result(
            "MRN999", "Multi Test", "Cocaine", "2024-01-25",
            "1980-01-01", "01/26/2024"
        )
        self.summary.log_positive_result(
            "MRN999", "Multi Test", "Marijuana", "2024-01-25",
            "1980-01-01", "01/26/2024"
        )

        output_path = generate_positives_summary_pdf(self.summary, self.test_dir, 3)
        self.assertTrue(os.path.exists(output_path))

        reader = PdfReader(output_path)
        page_text = reader.pages[0].extract_text()

        # Should show patient only once with all tests listed
        self.assertIn("Multi Test", page_text)
        self.assertIn("Opiates", page_text)
        self.assertIn("Cocaine", page_text)
        self.assertIn("Marijuana", page_text)

    def test_positive_summary_missing_dob(self):
        """Test handling of missing DOB field."""
        self.summary.log_positive_result(
            "MRN111", "No DOB Patient", "Opiates", "2024-01-30",
            "", "01/31/2024"  # Empty DOB
        )

        output_path = generate_positives_summary_pdf(self.summary, self.test_dir, 1)
        self.assertTrue(os.path.exists(output_path))

        reader = PdfReader(output_path)
        page_text = reader.pages[0].extract_text()
        self.assertIn("No DOB Patient", page_text)
        self.assertIn("N/A", page_text)  # Should show N/A for missing DOB

    def test_positive_summary_missing_dates(self):
        """Test handling of missing collection and completion dates."""
        self.summary.log_positive_result(
            "MRN222", "Missing Dates", "Cocaine", "",
            "1985-06-15", ""  # Empty dates
        )

        output_path = generate_positives_summary_pdf(self.summary, self.test_dir, 1)
        self.assertTrue(os.path.exists(output_path))

        reader = PdfReader(output_path)
        page_text = reader.pages[0].extract_text()
        self.assertIn("Missing Dates", page_text)

    def test_positive_summary_filename_timestamp(self):
        """Test that filename contains proper timestamp format."""
        self.summary.log_positive_result(
            "MRN333", "Test Patient", "Opiates", "2024-02-01",
            "1990-01-01", "02/02/2024"
        )

        before_time = datetime.now().strftime('%Y-%m-%d')
        output_path = generate_positives_summary_pdf(self.summary, self.test_dir, 1)
        filename = os.path.basename(output_path)

        # Check format: Positive_Results_Summary_YYYY-MM-DD_HHMMSS.pdf
        self.assertTrue(filename.startswith("Positive_Results_Summary_"))
        self.assertIn(before_time, filename)  # Should contain today's date
        self.assertTrue(filename.endswith(".pdf"))

    def test_positive_summary_output_location(self):
        """Test that summary is saved to main output directory."""
        # Create subdirectory structure
        sub_dir = os.path.join(self.test_dir, "2024-01-15")
        os.makedirs(sub_dir)

        self.summary.log_positive_result(
            "MRN444", "Location Test", "Opiates", "2024-01-15",
            "1980-01-01", "01/16/2024"
        )

        # Generate PDF in main directory
        output_path = generate_positives_summary_pdf(self.summary, self.test_dir, 1)

        # Verify saved to main directory, NOT subdirectory
        self.assertEqual(os.path.dirname(output_path), self.test_dir)
        self.assertFalse(output_path.startswith(sub_dir))

    def test_positive_summary_with_organized_output(self):
        """Test that summary works correctly even with organize-by options."""
        # Create organization subdirectories
        os.makedirs(os.path.join(self.test_dir, "MRN_123"))
        os.makedirs(os.path.join(self.test_dir, "MRN_456"))

        self.summary.log_positive_result(
            "MRN123", "Organized Patient 1", "Opiates", "2024-01-20",
            "1985-05-15", "01/21/2024"
        )
        self.summary.log_positive_result(
            "MRN456", "Organized Patient 2", "Cocaine", "2024-01-21",
            "1990-08-22", "01/22/2024"
        )

        output_path = generate_positives_summary_pdf(self.summary, self.test_dir, 2)

        # Should still be in root directory
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
                f"MRN{i:03d}", f"Patient {i}", f"Test {i % 5}",
                "2024-01-15", f"198{i % 10}-01-01", "01/16/2024"
            )

        output_path = generate_positives_summary_pdf(self.summary, self.test_dir, 50)
        self.assertTrue(os.path.exists(output_path))

        # Verify PDF was created successfully
        reader = PdfReader(output_path)
        self.assertGreater(len(reader.pages), 0)

        # Check that summary statistics are correct
        page_text = reader.pages[0].extract_text()
        self.assertIn("Positive Results Found: 50", page_text)

    def test_positive_summary_clia_header(self):
        """Test that CLIA laboratory header is included."""
        self.summary.log_positive_result(
            "MRN555", "Header Test", "Opiates", "2024-02-05",
            "1985-03-20", "02/06/2024"
        )

        output_path = generate_positives_summary_pdf(self.summary, self.test_dir, 1)
        reader = PdfReader(output_path)
        page_text = reader.pages[0].extract_text()

        # Check for CLIA header components
        self.assertIn("Therapeutic Life Choices", page_text)
        self.assertIn("CLIA ID: 37D2301589", page_text)

    def test_positive_summary_error_handling(self):
        """Test error handling for invalid output directory."""
        self.summary.log_positive_result(
            "MRN666", "Error Test", "Opiates", "2024-02-10",
            "1990-01-01", "02/11/2024"
        )

        # Try to write to non-existent directory with no permission
        invalid_dir = "/invalid/nonexistent/path"

        with self.assertRaises(Exception):
            generate_positives_summary_pdf(self.summary, invalid_dir, 1)


if __name__ == '__main__':
    unittest.main()
