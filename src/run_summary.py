"""This module defines the RunSummary class for collecting and displaying results.

The RunSummary class provides a centralized way to track statistics, warnings,
and errors throughout the application's execution. At the end of the process,
it can generate a formatted, human-readable summary of the entire run.
"""
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
        self._errors = []

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

    def log_error(self, identifier, message):
        """Logs a generic error encountered during processing."""
        self._errors.append(f"Identifier '{identifier}': {message}")


    def print_summary(self):
        """Prints the formatted run summary to the console."""
        print("\n" + "-" * 40)
        print("--- 📊 Automated Report Run Summary ---")
        print("-" * 40)

        # --- Successes ---
        print("\n✅ Successes")
        print(f"- Found {self._total_samples} unique patient samples.")
        print(f"- {self._pdfs_generated} PDF reports successfully generated.")
        if self._output_dir:
            print(f"- Reports saved to: {self._output_dir}")

        # --- Warnings & Skipped Items ---
        if self._skipped_samples or self._invalid_results:
            print("\n⚠️ Warnings & Skipped Items")
            if self._skipped_samples:
                print("- User skipped generating a report for the following samples:")
                for item in self._skipped_samples:
                    print(f"  - {item}")

            if self._invalid_results:
                print("- Invalid test results were found and excluded from the following reports:")
                for mrn, results in self._invalid_results.items():
                    print(f"  - Patient MR# {mrn}:")
                    for result_info in results:
                        print(f"    - {result_info}")

        # --- Errors ---
        if self._errors:
            print("\n❌ Errors Encountered")
            for error in self._errors:
                print(f"- {error}")

        print("\n" + "-" * 40)
        print("Process complete.")