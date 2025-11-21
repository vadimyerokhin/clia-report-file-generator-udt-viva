import unittest
import io
from src.run_summary import RunSummary

class TestRunSummary(unittest.TestCase):
    def setUp(self):
        self.summary = RunSummary()

    def test_initialization(self):
        self.assertEqual(self.summary._total_samples, 0)
        self.assertEqual(self.summary._pdfs_generated, 0)
        self.assertEqual(self.summary._pdfs_failed, 0)
        self.assertEqual(self.summary._output_dir, "")
        self.assertEqual(self.summary._skipped_samples, [])
        self.assertEqual(self.summary._invalid_results, {})
        self.assertEqual(self.summary.positive_results, [])
        self.assertEqual(self.summary._errors, [])

    def test_set_output_stream(self):
        string_io = io.StringIO()
        self.summary.set_output_stream(string_io)
        self.assertIs(self.summary.output_stream, string_io)

    def test_log_positive_result(self):
        self.summary.log_positive_result("MRN123", "John Doe", "Opiates", "2023-01-01")
        self.assertEqual(len(self.summary.positive_results), 1)
        self.assertEqual(self.summary.positive_results[0], {
            "mrn": "MRN123",
            "patient_name": "John Doe",
            "test_name": "Opiates",
            "collection_date": "2023-01-01"
        })

    def test_print_summary_all_sections(self):
        # Test summary with successes, warnings, skips, and errors
        output = io.StringIO()
        self.summary.set_output_stream(output)
        self.summary.set_total_samples(5)
        self.summary.log_success()
        self.summary.log_failure("MRN001", "PDF generation failed")
        self.summary.log_user_skip("MRN002", "2023-01-15", "S002")
        self.summary.log_invalid_result("MRN003", "TestA", "Invalid")
        self.summary.log_error("MRN004", "Generic error")
        self.summary.set_output_dir("/fake/dir")

        self.summary.print_summary()
        summary_output = output.getvalue()

        self.assertIn("5 unique patient samples", summary_output)
        self.assertIn("1 PDF reports successfully generated", summary_output)
        self.assertIn("Reports saved to: /fake/dir", summary_output)
        self.assertIn("⚠️ Warnings & Skipped Items", summary_output)
        self.assertIn("User skipped generating a report", summary_output)
        self.assertIn("Sample ID 'S002' for patient MR# MRN002 on 2023-01-15", summary_output)
        self.assertIn("Invalid test results were found", summary_output)
        self.assertIn("Patient MR# MRN003:", summary_output)
        self.assertIn("TestA: 'Invalid'", summary_output)
        self.assertIn("❌ Errors Encountered", summary_output)
        self.assertIn("Identifier 'MRN004': Generic error", summary_output)
        self.assertIn("Patient/Sample 'MRN001': PDF generation failed", summary_output)

    def test_print_summary_only_success(self):
        # Test summary with only success messages
        output = io.StringIO()
        self.summary.set_output_stream(output)
        self.summary.set_total_samples(3)
        self.summary.log_success()
        self.summary.log_success()
        self.summary.log_success()

        self.summary.print_summary()
        summary_output = output.getvalue()

        self.assertIn("3 unique patient samples", summary_output)
        self.assertIn("3 PDF reports successfully generated", summary_output)
        self.assertNotIn("⚠️ Warnings & Skipped Items", summary_output)
        self.assertNotIn("❌ Errors Encountered", summary_output)

if __name__ == '__main__':
    unittest.main()