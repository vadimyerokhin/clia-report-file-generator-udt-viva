"""This module defines the exporter framework for generating reports in different formats."""
from abc import ABC, abstractmethod
from pdf_generator import generate_pdf_report

class Exporter(ABC):
    """Abstract base class for all exporters."""
    @abstractmethod
    def export_report(self, data, output_path, summary, completed_date, input_file):
        """Exports a report to the given output path."""
        pass

class PdfExporter(Exporter):
    """Exporter for generating PDF reports."""
    def __init__(self):
        self.pdf_generated_callback = None

    def set_pdf_generated_callback(self, callback):
        self.pdf_generated_callback = callback

    def export_report(self, data, output_path, summary, completed_date, input_file):
        """Exports a PDF report."""
        generate_pdf_report(data, output_path, summary, completed_date, input_file)
        if self.pdf_generated_callback:
            self.pdf_generated_callback(output_path)
