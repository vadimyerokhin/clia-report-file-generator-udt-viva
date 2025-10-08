"""This module defines the RunSummary class for collecting and displaying results.

The RunSummary class provides a centralized way to track statistics, warnings,
and errors throughout the application's execution. At the end of the process,
it can generate a formatted, human-readable summary of the entire run.
"""
import sys
from collections import defaultdict

class RunSummary:
    """A class to collect and display a summary of the application's execution."""

    def __init__(self):
        """Initializes the RunSummary instance."""
        self._total_samples = 0
        self._pdfs_generated = 0
        self._pdfs_failed = 0
        self._output_dir = ""
        self._skipped_samples = []
        self._invalid_results = defaultdict(list)
        self._positive_results = []
        self._errors = []
        self.output_stream = sys.stdout

    def set_output_stream(self, stream):
        """Sets the output stream for the summary printout."""
        self.output_stream = stream

    def set_total_samples(self, count):
        """Sets the total number of unique patient samples found."""
        self._total_samples = count

    def set_output_dir(self, path):
        """Sets the path to the output directory."""
        self._output_dir = path

    def log_success(self):
        """Increments the counter for successfully generated PDFs."""
        self._pdfs_generated += 1

    def log_failure(self, identifier, reason):
        """Increments the counter for failed PDFs and logs the error."""
        self._pdfs_failed += 1
        self._errors.append(f"Patient/Sample '{identifier}': {reason}")

    def log_user_skip(self, mrn, date_collected, sample_id):
        """Logs when a user chooses to skip a sample during conflict resolution."""
        self._skipped_samples.append(
            f"Sample ID '{sample_id}' for patient MR# {mrn} on {date_collected}"
        )

    def log_invalid_result(self, mrn, test_name, result):
        """Logs a test result that was filtered out as invalid."""
        self._invalid_results[mrn].append(f"{test_name}: '{result}'")

    def log_positive_result(self, mrn, patient_name, test_name, collection_date):
        """Logs a positive test result for the summary report."""
        self._positive_results.append({
            "mrn": mrn,
            "patient_name": patient_name,
            "test_name": test_name,
            "collection_date": collection_date
        })

    def log_error(self, identifier, message):
        """Logs a generic error encountered during processing."""
        self._errors.append(f"Identifier '{identifier}': {message}")


    def print_summary(self):
        """Prints the formatted run summary to the configured output stream."""
        print("\n" + "-" * 40, file=self.output_stream)
        print("--- 📊 Automated Report Run Summary ---", file=self.output_stream)
        print("-" * 40, file=self.output_stream)

        # --- Successes ---
        print("\n✅ Successes", file=self.output_stream)
        print(f"- Found {self._total_samples} unique patient samples.", file=self.output_stream)
        print(f"- {self._pdfs_generated} PDF reports successfully generated.", file=self.output_stream)
        if self._output_dir:
            print(f"- Reports saved to: {self._output_dir}", file=self.output_stream)

        # --- Warnings & Skipped Items ---
        if self._skipped_samples or self._invalid_results:
            print("\n⚠️ Warnings & Skipped Items", file=self.output_stream)
            if self._skipped_samples:
                print("- User skipped generating a report for the following samples:", file=self.output_stream)
                for item in self._skipped_samples:
                    print(f"  - {item}", file=self.output_stream)

            if self._invalid_results:
                print("- Invalid test results were found and excluded from the following reports:", file=self.output_stream)
                for mrn, results in self._invalid_results.items():
                    print(f"  - Patient MR# {mrn}:", file=self.output_stream)
                    for result_info in results:
                        print(f"    - {result_info}", file=self.output_stream)

        # --- Errors ---
        if self._errors:
            print("\n❌ Errors Encountered", file=self.output_stream)
            for error in self._errors:
                print(f"- {error}", file=self.output_stream)

        print("\n" + "-" * 40, file=self.output_stream)
        print("Process complete.", file=self.output_stream)