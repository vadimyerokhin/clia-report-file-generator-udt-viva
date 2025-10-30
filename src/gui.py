# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pandas",
#     "pyside6",
#     "reportlab",
# ]
# ///
"""GUI interface for PDF Laboratory Report Generator.

Provides a user-friendly interface for generating CLIA-compliant laboratory reports
with persistent configuration, drag-and-drop support, and real-time progress tracking.
"""
import sys
import io
import os
from pathlib import Path
from PySide6.QtCore import QThread, Signal, Slot, QObject, Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog, QGroupBox, QRadioButton,
    QTextEdit, QMessageBox, QDialog, QDialogButtonBox, QListWidget, QCheckBox,
    QComboBox, QFrame
)
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtPdf import QPdfDocument

# Fix imports to work from project root
try:
    from src.main import generate_reports
    from src.run_summary import RunSummary
    from src.exporter import PdfExporter
    from src.pdf_generator import generate_positives_summary_pdf
    from src.config_manager import ConfigManager
except ImportError:
    # Fallback for running directly from src directory
    from main import generate_reports
    from run_summary import RunSummary
    from exporter import PdfExporter
    from pdf_generator import generate_positives_summary_pdf
    from config_manager import ConfigManager


class WelcomeScreen(QDialog):
    """Welcome dialog shown on first launch or when requested."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Welcome")
        self.setMinimumWidth(500)
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("PDF Laboratory Report Generator")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)

        # Description
        message = QLabel(
            "Generate CLIA-compliant laboratory reports from CSV data.\n\n"
            "Features:\n"
            "• Drag and drop CSV files for easy input\n"
            "• Organize reports by collection date, test date, or MRN\n"
            "• Generate positive results summary\n"
            "• Real-time progress tracking and PDF preview\n"
            "• Settings automatically saved between sessions\n\n"
            "To get started, select an input CSV file and output directory."
        )
        message.setWordWrap(True)
        layout.addWidget(message)

        # Don't show again checkbox
        self.dont_show_again = QCheckBox("Don't show this message again")
        layout.addWidget(self.dont_show_again)

        # Get started button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.get_started_button = QPushButton("Get Started")
        self.get_started_button.setDefault(True)
        self.get_started_button.clicked.connect(self.accept)
        button_layout.addWidget(self.get_started_button)
        layout.addLayout(button_layout)


class DragDropLineEdit(QLineEdit):
    """QLineEdit with drag-and-drop support for files and folders."""

    def __init__(self, parent=None, accept_dirs=False):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.accept_dirs = accept_dirs

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            url = event.mimeData().urls()[0]
            if url.isLocalFile():
                path = url.toLocalFile()
                # Validate path type
                if self.accept_dirs and os.path.isdir(path):
                    self.setText(path)
                elif not self.accept_dirs and os.path.isfile(path):
                    self.setText(path)
        else:
            event.ignore()


class Worker(QObject):
    """Background worker for report generation.

    Runs in separate thread to prevent GUI freezing during long operations.
    """

    finished = Signal()
    progress = Signal(str)
    conflict = Signal(str, str, list)
    conflict_resolved = Signal(int)
    pdf_generated = Signal(str)

    def __init__(self, input_file, output_dir, organize_by, generate_positive_summary, exporter):
        super().__init__()
        self.input_file = input_file
        self.output_dir = output_dir
        self.organize_by = organize_by
        self.generate_positive_summary = generate_positive_summary
        self.summary = RunSummary()
        self.user_choice = -1
        self.exporter = exporter

    def run(self):
        """Execute report generation workflow."""
        self.summary.set_output_stream(io.StringIO())

        def progress_callback(message):
            self.progress.emit(message)

        def conflict_handler(mrn, date_collected, sample_ids):
            self.conflict.emit(mrn, date_collected, list(sample_ids))
            # Block until main thread provides resolution
            return self.user_choice

        def pdf_generated_callback(path):
            self.pdf_generated.emit(path)

        self.exporter.set_pdf_generated_callback(pdf_generated_callback)

        generate_reports(
            self.input_file,
            self.output_dir,
            self.organize_by,
            self.summary,
            self.exporter,
            progress_callback,
            conflict_handler
        )

        # Generate positive results summary if enabled
        if self.generate_positive_summary:
            try:
                self.progress.emit("\nGenerating positive results summary PDF...")
                output_path = generate_positives_summary_pdf(
                    self.summary,
                    self.output_dir,
                    self.summary._total_samples
                )
                self.progress.emit(f"Successfully generated positive results summary: {output_path}")
            except Exception as e:
                self.progress.emit(f"Error generating positive results summary PDF: {e}")
                self.summary.log_error("Positive Summary PDF", str(e))
        else:
            self.progress.emit("\nPositive results summary generation disabled.")

        # Append summary to progress
        summary_output = self.summary.output_stream.getvalue()
        self.progress.emit("\n" + "=" * 60)
        self.progress.emit("RUN SUMMARY")
        self.progress.emit("=" * 60)
        self.progress.emit(summary_output)
        self.finished.emit()

    @Slot(int)
    def on_conflict_resolved(self, choice):
        """Handle user's conflict resolution choice."""
        self.user_choice = choice


class SelectSampleDialog(QDialog):
    """Dialog for resolving duplicate sample conflicts."""

    def __init__(self, parent, mrn, date_collected, sample_ids):
        super().__init__(parent)
        self.setWindowTitle("Multiple Samples Found")
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)

        message = QLabel(
            f"Multiple samples found for:\n"
            f"MRN: {mrn}\n"
            f"Date: {date_collected}\n\n"
            f"Please select a sample to process or click Skip to skip this patient."
        )
        layout.addWidget(message)

        self.sample_list = QListWidget()
        for sample_id in sample_ids:
            self.sample_list.addItem(f"Sample ID: {sample_id}")
        self.sample_list.setCurrentRow(0)
        layout.addWidget(self.sample_list)

        # Custom buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        skip_button = QPushButton("Skip")
        skip_button.clicked.connect(self.reject)
        button_layout.addWidget(skip_button)

        select_button = QPushButton("Select")
        select_button.setDefault(True)
        select_button.clicked.connect(self.accept)
        button_layout.addWidget(select_button)

        layout.addLayout(button_layout)

    def get_selected_sample_index(self):
        """Get index of selected sample."""
        return self.sample_list.currentRow()


class MainWindow(QMainWindow):
    """Main application window with persistent configuration."""

    def __init__(self, config_manager: ConfigManager = None):
        super().__init__()
        self.config_manager = config_manager or ConfigManager()
        self.config = self.config_manager.load_config()
        self._setup_ui()
        self._load_saved_state()
        self._apply_validation()

    def _setup_ui(self):
        """Initialize user interface components."""
        self.setWindowTitle("PDF Laboratory Report Generator")

        # Restore window geometry or use defaults
        geom = self.config.get("window_geometry", {})
        width = geom.get("width", 1200)
        height = geom.get("height", 800)
        x = geom.get("x")
        y = geom.get("y")

        if x is not None and y is not None:
            self.setGeometry(x, y, width, height)
        else:
            self.resize(width, height)

        # Central widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setSpacing(10)

        # Left panel (controls)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(10)
        main_layout.addWidget(left_panel, 1)

        # Right panel (log and preview)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(10)
        main_layout.addWidget(right_panel, 2)

        # File Selection Group
        file_group = QGroupBox("File Selection")
        file_layout = QVBoxLayout()
        file_layout.setSpacing(8)

        # Input file
        input_label = QLabel("Input CSV File:")
        file_layout.addWidget(input_label)

        input_layout = QHBoxLayout()
        self.input_field = DragDropLineEdit(accept_dirs=False)
        self.input_field.setPlaceholderText("Select or drag CSV file here...")
        self.input_field.textChanged.connect(self._validate_inputs)
        input_layout.addWidget(self.input_field)

        self.input_button = QPushButton("Browse...")
        self.input_button.clicked.connect(self.browse_input_file)
        input_layout.addWidget(self.input_button)
        file_layout.addLayout(input_layout)

        # Recent files dropdown
        recent_files = self.config_manager.get_recent_files()
        if recent_files:
            recent_layout = QHBoxLayout()
            recent_label = QLabel("Recent:")
            recent_layout.addWidget(recent_label)

            self.recent_files_combo = QComboBox()
            self.recent_files_combo.addItem("-- Select Recent File --")
            for f in recent_files:
                self.recent_files_combo.addItem(Path(f).name, f)
            self.recent_files_combo.currentIndexChanged.connect(self._on_recent_file_selected)
            recent_layout.addWidget(self.recent_files_combo)
            file_layout.addLayout(recent_layout)

        # Output directory
        output_label = QLabel("Output Directory:")
        file_layout.addWidget(output_label)

        output_layout = QHBoxLayout()
        self.output_field = DragDropLineEdit(accept_dirs=True)
        self.output_field.setPlaceholderText("Select or drag output folder here...")
        self.output_field.textChanged.connect(self._validate_inputs)
        output_layout.addWidget(self.output_field)

        self.output_button = QPushButton("Browse...")
        self.output_button.clicked.connect(self.browse_output_directory)
        output_layout.addWidget(self.output_button)
        file_layout.addLayout(output_layout)

        # Recent dirs dropdown
        recent_dirs = self.config_manager.get_recent_dirs()
        if recent_dirs:
            recent_dir_layout = QHBoxLayout()
            recent_dir_label = QLabel("Recent:")
            recent_dir_layout.addWidget(recent_dir_label)

            self.recent_dirs_combo = QComboBox()
            self.recent_dirs_combo.addItem("-- Select Recent Directory --")
            for d in recent_dirs:
                self.recent_dirs_combo.addItem(Path(d).name, d)
            self.recent_dirs_combo.currentIndexChanged.connect(self._on_recent_dir_selected)
            recent_dir_layout.addWidget(self.recent_dirs_combo)
            file_layout.addLayout(recent_dir_layout)

        file_group.setLayout(file_layout)
        left_layout.addWidget(file_group)

        # Report Organization Group
        org_group = QGroupBox("Report Organization")
        org_layout = QVBoxLayout()
        org_layout.setSpacing(5)

        self.org_none = QRadioButton("None (flat structure)")
        self.org_none.setToolTip("All reports in one directory")
        self.org_collection = QRadioButton("By Collection Date")
        self.org_collection.setToolTip("Organize reports by specimen collection date")
        self.org_tested = QRadioButton("By Test Date")
        self.org_tested.setToolTip("Organize reports by test completion date")
        self.org_mrn = QRadioButton("By Medical Record Number")
        self.org_mrn.setToolTip("Organize reports by patient MRN")

        org_layout.addWidget(self.org_none)
        org_layout.addWidget(self.org_collection)
        org_layout.addWidget(self.org_tested)
        org_layout.addWidget(self.org_mrn)

        org_group.setLayout(org_layout)
        left_layout.addWidget(org_group)

        # Summary Options Group
        summary_group = QGroupBox("Summary Options")
        summary_layout = QVBoxLayout()
        summary_layout.setSpacing(5)

        self.generate_positive_summary_checkbox = QCheckBox("Generate Positive Results Summary")
        self.generate_positive_summary_checkbox.setToolTip(
            "Creates a separate PDF with all positive test results"
        )
        summary_layout.addWidget(self.generate_positive_summary_checkbox)

        summary_group.setLayout(summary_layout)
        left_layout.addWidget(summary_group)

        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(5)

        self.reset_button = QPushButton("Reset Settings")
        self.reset_button.setToolTip("Reset all settings to defaults")
        self.reset_button.clicked.connect(self._reset_settings)
        button_layout.addWidget(self.reset_button)

        button_layout.addStretch()

        self.generate_button = QPushButton("Generate Reports")
        self.generate_button.setToolTip("Start report generation process")
        self.generate_button.setStyleSheet("font-weight: bold; padding: 8px;")
        self.generate_button.clicked.connect(self.start_report_generation)
        button_layout.addWidget(self.generate_button)

        left_layout.addLayout(button_layout)

        # Log Group
        log_group = QGroupBox("Progress Log")
        log_layout = QVBoxLayout()
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("font-family: monospace;")
        log_layout.addWidget(self.log_area)
        log_group.setLayout(log_layout)
        right_layout.addWidget(log_group, 2)

        # PDF Preview Group
        pdf_preview_group = QGroupBox("PDF Preview")
        pdf_preview_layout = QVBoxLayout()
        self.pdf_preview = QPdfView()
        pdf_preview_layout.addWidget(self.pdf_preview)
        pdf_preview_group.setLayout(pdf_preview_layout)
        right_layout.addWidget(pdf_preview_group, 3)

        self.pdf_document = QPdfDocument(self)

        # Status bar
        self.statusBar().showMessage("Ready")

    def _load_saved_state(self):
        """Load saved configuration into UI elements."""
        # Load file paths
        last_input = self.config.get("last_input_file", "")
        if last_input and os.path.exists(last_input):
            self.input_field.setText(last_input)

        last_output = self.config.get("last_output_dir", "")
        if last_output and os.path.isdir(last_output):
            self.output_field.setText(last_output)

        # Load organization option
        org_option = self.config.get("organization_option", "none")
        if org_option == "collection-date":
            self.org_collection.setChecked(True)
        elif org_option == "tested-date":
            self.org_tested.setChecked(True)
        elif org_option == "mrn":
            self.org_mrn.setChecked(True)
        else:
            self.org_none.setChecked(True)

        # Load summary checkbox
        generate_summary = self.config.get("generate_positive_summary", True)
        self.generate_positive_summary_checkbox.setChecked(generate_summary)

    def _save_current_state(self):
        """Save current UI state to configuration."""
        updates = {
            "last_input_file": self.input_field.text(),
            "last_output_dir": self.output_field.text(),
            "organization_option": self.get_organization_option() or "none",
            "generate_positive_summary": self.generate_positive_summary_checkbox.isChecked(),
            "window_geometry": {
                "width": self.width(),
                "height": self.height(),
                "x": self.x(),
                "y": self.y()
            }
        }
        self.config_manager.update(updates)
        self.config_manager.save_config()

    def _validate_inputs(self):
        """Validate input fields and enable/disable generate button."""
        input_file = self.input_field.text()
        output_dir = self.output_field.text()

        # Check if files exist (ensure boolean results)
        input_valid = bool(input_file and os.path.isfile(input_file))
        output_valid = bool(output_dir and os.path.isdir(output_dir))

        # Update button state
        self.generate_button.setEnabled(input_valid and output_valid)

        # Update status bar
        if not input_valid and input_file:
            self.statusBar().showMessage("Invalid input file", 3000)
        elif not output_valid and output_dir:
            self.statusBar().showMessage("Invalid output directory", 3000)
        elif input_valid and output_valid:
            self.statusBar().showMessage("Ready to generate reports")
        else:
            self.statusBar().showMessage("Ready")

    def _apply_validation(self):
        """Apply initial validation."""
        self._validate_inputs()

    def _on_recent_file_selected(self, index):
        """Handle recent file selection."""
        if index > 0:  # Skip first item (placeholder)
            path = self.recent_files_combo.itemData(index)
            if path and os.path.exists(path):
                self.input_field.setText(path)

    def _on_recent_dir_selected(self, index):
        """Handle recent directory selection."""
        if index > 0:  # Skip first item (placeholder)
            path = self.recent_dirs_combo.itemData(index)
            if path and os.path.isdir(path):
                self.output_field.setText(path)

    def _reset_settings(self):
        """Reset all settings to defaults."""
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Are you sure you want to reset all settings to defaults?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.config_manager.reset_to_defaults()
            self.config = self.config_manager.load_config()
            self._load_saved_state()
            self.statusBar().showMessage("Settings reset to defaults", 3000)

    def show_welcome_screen(self):
        """Show welcome dialog if enabled."""
        if self.config.get("show_welcome", True):
            welcome = WelcomeScreen(self)
            if welcome.exec() == QDialog.Accepted:
                if welcome.dont_show_again.isChecked():
                    self.config_manager.set("show_welcome", False)
                    self.config_manager.save_config()

    @Slot()
    def browse_input_file(self):
        """Open file browser for input CSV selection."""
        # Start from last used directory or home
        start_dir = ""
        if self.input_field.text() and os.path.exists(self.input_field.text()):
            start_dir = str(Path(self.input_field.text()).parent)

        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Select Input CSV",
            start_dir,
            "CSV Files (*.csv);;All Files (*)"
        )
        if filepath:
            self.input_field.setText(filepath)

    @Slot()
    def browse_output_directory(self):
        """Open directory browser for output selection."""
        # Start from last used directory or home
        start_dir = self.output_field.text() if os.path.isdir(self.output_field.text()) else ""

        dirpath = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            start_dir
        )
        if dirpath:
            self.output_field.setText(dirpath)

    @Slot(str)
    def load_pdf(self, path):
        """Load PDF into preview pane."""
        if os.path.exists(path):
            self.pdf_document.load(path)
            self.pdf_preview.setDocument(self.pdf_document)

    @Slot()
    def start_report_generation(self):
        """Start report generation in background thread."""
        input_file = self.input_field.text()
        output_dir = self.output_field.text()

        # Final validation
        if not input_file or not os.path.isfile(input_file):
            QMessageBox.warning(self, "Invalid Input", "Please select a valid input CSV file.")
            return

        if not output_dir or not os.path.isdir(output_dir):
            QMessageBox.warning(self, "Invalid Output", "Please select a valid output directory.")
            return

        # Add to recent lists
        self.config_manager.add_recent_file(input_file)
        self.config_manager.add_recent_dir(output_dir)

        # Save current state
        self._save_current_state()

        # Clear log and show start message
        self.log_area.clear()
        self.log_area.append("=" * 60)
        self.log_area.append("STARTING REPORT GENERATION")
        self.log_area.append("=" * 60)
        self.log_area.append(f"Input: {input_file}")
        self.log_area.append(f"Output: {output_dir}")
        self.log_area.append(f"Organization: {self.get_organization_option() or 'None'}")
        self.log_area.append(f"Positive Summary: {'Yes' if self.generate_positive_summary_checkbox.isChecked() else 'No'}")
        self.log_area.append("=" * 60)
        self.log_area.append("")

        # Disable UI during generation
        self.generate_button.setEnabled(False)
        self.input_button.setEnabled(False)
        self.output_button.setEnabled(False)
        self.statusBar().showMessage("Generating reports...")

        # Create worker and thread
        exporter = PdfExporter()
        self.thread = QThread()
        self.worker = Worker(
            input_file,
            output_dir,
            self.get_organization_option(),
            self.generate_positive_summary_checkbox.isChecked(),
            exporter
        )
        self.worker.moveToThread(self.thread)

        # Connect signals
        self.worker.progress.connect(self.log_area.append)
        self.worker.conflict.connect(self.handle_conflict)
        self.worker.pdf_generated.connect(self.load_pdf)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self._on_generation_complete)

        # Start processing
        self.thread.start()

    def _on_generation_complete(self):
        """Handle completion of report generation."""
        self.generate_button.setEnabled(True)
        self.input_button.setEnabled(True)
        self.output_button.setEnabled(True)
        self._validate_inputs()
        self.statusBar().showMessage("Report generation complete", 5000)

    def get_organization_option(self):
        """Get selected organization option.

        Returns:
            Organization option string or None
        """
        if self.org_collection.isChecked():
            return "collection-date"
        if self.org_tested.isChecked():
            return "tested-date"
        if self.org_mrn.isChecked():
            return "mrn"
        return None

    @Slot(str, str, list)
    def handle_conflict(self, mrn, date_collected, sample_ids):
        """Handle duplicate sample conflict.

        Args:
            mrn: Medical record number
            date_collected: Collection date
            sample_ids: List of conflicting sample IDs
        """
        dialog = SelectSampleDialog(self, mrn, date_collected, sample_ids)
        if dialog.exec() == QDialog.Accepted:
            choice = dialog.get_selected_sample_index()
            self.worker.on_conflict_resolved(choice)
        else:
            self.worker.on_conflict_resolved(-1)  # Skip

    def closeEvent(self, event):
        """Handle window close event.

        Saves current state before closing.
        """
        self._save_current_state()
        event.accept()


def main():
    """Entry point for GUI application."""
    app = QApplication(sys.argv)
    app.setApplicationName("PDF Laboratory Report Generator")

    config_manager = ConfigManager()
    window = MainWindow(config_manager)
    window.show_welcome_screen()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
