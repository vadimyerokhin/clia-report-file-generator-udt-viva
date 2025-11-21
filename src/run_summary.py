"""This module defines the RunSummary class for collecting and displaying results.

The RunSummary class provides a centralized way to track statistics, warnings,
and errors throughout the application's execution. At the end of the process,
it can generate a formatted, human-readable summary of the entire run.
"""
import sys
from collections import defaultdict
from typing import Any, TextIO


class RunSummary:
    """A class to collect and display a summary of the application's execution."""

    def __init__(self) -> None:
        """Initializes the RunSummary instance."""
        self._total_samples: int = 0
        self._pdfs_generated: int = 0
        self._pdfs_failed: int = 0
        self._output_dir: str = ""
        self._skipped_samples: list[str] = []
        self._invalid_results: defaultdict[Any, list[str]] = defaultdict(list)
        self._positive_results: list[dict[str, Any]] = []
        self._errors: list[str] = []
        self._billing_entries: int = 0
        self._billing_file_path: str = ""
        self._billing_errors: list[str] = []
        self.output_stream: TextIO = sys.stdout

    @property
    def positive_results(self) -> list[dict[str, Any]]:
        """Returns the list of positive results."""
        return self._positive_results

    @property
    def pdfs_generated(self) -> int:
        """Returns the number of PDFs successfully generated."""
        return self._pdfs_generated

    @property
    def total_samples(self) -> int:
        """Returns the total number of samples processed."""
        return self._total_samples

    def set_output_stream(self, stream: TextIO) -> None:
        """Sets the output stream for the summary printout."""
        self.output_stream = stream

    def set_total_samples(self, count: int) -> None:
        """Sets the total number of unique patient samples found."""
        self._total_samples = count

    def set_output_dir(self, path: str) -> None:
        """Sets the path to the output directory."""
        self._output_dir = path

    def log_success(self) -> None:
        """Increments the counter for successfully generated PDFs."""
        self._pdfs_generated += 1

    def log_failure(self, identifier: str, reason: str) -> None:
        """Increments the counter for failed PDFs and logs the error."""
        self._pdfs_failed += 1
        self._errors.append(f"Patient/Sample '{identifier}': {reason}")

    def log_user_skip(self, mrn: Any, date_collected: Any, sample_id: Any) -> None:
        """Logs when a user chooses to skip a sample during conflict resolution."""
        self._skipped_samples.append(
            f"Sample ID '{sample_id}' for patient MR# {mrn} on {date_collected}"
        )

    def log_invalid_result(self, mrn: Any, test_name: str, result: str) -> None:
        """Logs a test result that was filtered out as invalid."""
        self._invalid_results[mrn].append(f"{test_name}: '{result}'")

    def log_positive_result(
        self, mrn: Any, patient_name: str, test_name: str, collection_date: Any
    ) -> None:
        """Logs a positive test result for the summary report."""
        self._positive_results.append({
            "mrn": mrn,
            "patient_name": patient_name,
            "test_name": test_name,
            "collection_date": collection_date
        })

    def log_error(self, identifier: str, message: str) -> None:
        """Logs a generic error encountered during processing."""
        self._errors.append(f"Identifier '{identifier}': {message}")

    def log_billing_success(self) -> None:
        """Increments the counter for successfully created billing entries."""
        self._billing_entries += 1

    def log_billing_failure(self, identifier: str, reason: str) -> None:
        """Logs when a billing entry could not be created."""
        self._billing_errors.append(f"Billing entry '{identifier}': {reason}")

    def set_billing_file_path(self, path: str) -> None:
        """Sets the path to the generated billing file."""
        self._billing_file_path = path

    def get_billing_count(self) -> int:
        """Returns the total number of billing entries created."""
        return self._billing_entries


    def print_summary(self) -> None:
        """Prints the formatted run summary to the configured output stream."""
        print("\n" + "-" * 40, file=self.output_stream)
        print("--- 📊 Automated Report Run Summary ---", file=self.output_stream)
        print("-" * 40, file=self.output_stream)

        # --- Successes ---
        print("\n✅ Successes", file=self.output_stream)
        print(f"- Found {self._total_samples} unique patient samples.", file=self.output_stream)
        print(f"- {self._pdfs_generated} PDF reports successfully generated.", file=self.output_stream)
        if self._billing_entries > 0:
            print(f"- {self._billing_entries} billing entries created (CPT 80307).", file=self.output_stream)
        if self._output_dir:
            print(f"- Reports saved to: {self._output_dir}", file=self.output_stream)
        if self._billing_file_path:
            print(f"- Billing file saved to: {self._billing_file_path}", file=self.output_stream)

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
        if self._errors or self._billing_errors:
            print("\n❌ Errors Encountered", file=self.output_stream)
            for error in self._errors:
                print(f"- {error}", file=self.output_stream)
            for error in self._billing_errors:
                print(f"- {error}", file=self.output_stream)

        print("\n" + "-" * 40, file=self.output_stream)
        print("Process complete.", file=self.output_stream)