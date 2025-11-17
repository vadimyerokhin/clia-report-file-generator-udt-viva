# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pandas",
#     "pyside6",
#     "reportlab",
# ]
# ///
import sys
import os
import io
import subprocess
import platform
from PySide6.QtCore import QThread, Signal, Slot, QObject, QEventLoop
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog, QGroupBox, QRadioButton,
    QTextEdit, QMessageBox, QDialog, QDialogButtonBox, QListWidget, QProgressBar
)
from PySide6.QtGui import QFont
from main import generate_reports, generate_positives_summary_pdf
from run_summary import RunSummary
from config import POSITIVES_SUMMARY_FILENAME

class Worker(QObject):
    finished = Signal()
    progress = Signal(str)
    progress_update = Signal(int, int)  # current, total
    conflict = Signal(str, str, list)
    error = Signal(str, str)  # title, message

    def __init__(self, input_file, output_dir, organize_by):
        super().__init__()
        self.input_file = input_file
        self.output_dir = output_dir
        self.organize_by = organize_by
        self.summary = RunSummary()
        self.user_choice = -1
        self.conflict_loop = None

    def run(self):
        try:
            self.summary.set_output_stream(io.StringIO())

            def progress_callback(message):
                self.progress.emit(message)

            def conflict_handler(mrn, date_collected, sample_ids):
                # Create an event loop to block this thread until user responds
                self.conflict_loop = QEventLoop()
                self.user_choice = -1

                # Emit signal to show dialog on main thread
                self.conflict.emit(mrn, date_collected, list(sample_ids))

                # Block this thread until user responds
                self.conflict_loop.exec()

                return self.user_choice

            generate_reports(self.input_file, self.output_dir, self.organize_by,
                           self.summary, progress_callback, conflict_handler)

            # Generate the positives summary PDF
            try:
                generate_positives_summary_pdf(self.summary, self.output_dir)
                if self.summary._positive_results:
                    summary_path = os.path.join(self.output_dir, POSITIVES_SUMMARY_FILENAME)
                    self.progress.emit(f"\n✅ Positives summary PDF generated: {summary_path}")
            except Exception as e:
                self.progress.emit(f"\n⚠️  Error generating positives summary PDF: {e}")

            # Append summary to progress
            summary_output = self.summary.output_stream.getvalue()
            self.progress.emit("\n" + "="*40 + "\n📊 Run Summary\n" + "="*40)
            self.progress.emit(summary_output)

            # Success message
            if self.summary._pdfs_generated > 0:
                self.progress.emit(f"\n🎉 Successfully generated {self.summary._pdfs_generated} report(s)!")

        except Exception as e:
            self.error.emit("Error During Processing", str(e))
            self.progress.emit(f"\n❌ Fatal error: {e}")
        finally:
            self.finished.emit()

    @Slot(int)
    def on_conflict_resolved(self, choice):
        self.user_choice = choice
        # Quit the event loop to unblock the worker thread
        if self.conflict_loop and self.conflict_loop.isRunning():
            self.conflict_loop.quit()

class SelectSampleDialog(QDialog):
    def __init__(self, parent, mrn, date_collected, sample_ids):
        super().__init__(parent)
        self.setWindowTitle("⚠️  Conflict: Multiple Samples Found")
        self.setMinimumWidth(400)
        self.layout = QVBoxLayout(self)

        # Header message
        message = QLabel(
            f"<b>Multiple samples found for patient:</b><br>"
            f"MR# {mrn} on {date_collected}<br><br>"
            f"Please select which sample to process:"
        )
        message.setWordWrap(True)
        self.layout.addWidget(message)

        # Sample list
        self.sample_list = QListWidget()
        for i, sample_id in enumerate(sample_ids):
            self.sample_list.addItem(f"Sample ID: {sample_id}")
        self.sample_list.setCurrentRow(0)  # Select first by default
        self.layout.addWidget(self.sample_list)

        # Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def get_selected_sample_index(self):
        return self.sample_list.currentRow()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🧪 PDF Laboratory Report Generator")
        self.setGeometry(100, 100, 900, 700)
        self.setMinimumSize(700, 500)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # File Selection Group
        file_group = QGroupBox("📁 File Selection")
        file_layout = QVBoxLayout()

        # Input file selection
        input_layout = QHBoxLayout()
        input_label_text = QLabel("Input CSV:")
        input_label_text.setMinimumWidth(80)
        self.input_label = QLineEdit("Select input CSV file...")
        self.input_label.setReadOnly(True)
        self.input_label.setPlaceholderText("No file selected")
        self.input_button = QPushButton("Browse...")
        self.input_button.setMinimumWidth(100)
        self.input_button.clicked.connect(self.browse_input_file)
        input_layout.addWidget(input_label_text)
        input_layout.addWidget(self.input_label)
        input_layout.addWidget(self.input_button)
        file_layout.addLayout(input_layout)

        # Output directory selection
        output_layout = QHBoxLayout()
        output_label_text = QLabel("Output Dir:")
        output_label_text.setMinimumWidth(80)
        self.output_label = QLineEdit("Select output directory...")
        self.output_label.setReadOnly(True)
        self.output_label.setPlaceholderText("No directory selected")
        self.output_button = QPushButton("Browse...")
        self.output_button.setMinimumWidth(100)
        self.output_button.clicked.connect(self.browse_output_directory)
        output_layout.addWidget(output_label_text)
        output_layout.addWidget(self.output_label)
        output_layout.addWidget(self.output_button)
        file_layout.addLayout(output_layout)

        file_group.setLayout(file_layout)
        main_layout.addWidget(file_group)

        # Report Organization Group
        org_group = QGroupBox("📂 Report Organization")
        org_layout = QHBoxLayout()
        self.org_none = QRadioButton("None (flat structure)")
        self.org_none.setChecked(True)
        self.org_collection = QRadioButton("By Collection Date")
        self.org_tested = QRadioButton("By Tested Date")
        self.org_mrn = QRadioButton("By MRN")
        org_layout.addWidget(self.org_none)
        org_layout.addWidget(self.org_collection)
        org_layout.addWidget(self.org_tested)
        org_layout.addWidget(self.org_mrn)
        org_group.setLayout(org_layout)
        main_layout.addWidget(org_group)

        # Action Buttons
        button_layout = QHBoxLayout()
        self.generate_button = QPushButton("🚀 Generate Reports")
        self.generate_button.setMinimumHeight(40)
        font = QFont()
        font.setBold(True)
        font.setPointSize(11)
        self.generate_button.setFont(font)
        self.generate_button.clicked.connect(self.start_report_generation)

        self.open_folder_button = QPushButton("📂 Open Output Folder")
        self.open_folder_button.setMinimumHeight(40)
        self.open_folder_button.clicked.connect(self.open_output_folder)
        self.open_folder_button.setEnabled(False)

        button_layout.addWidget(self.generate_button)
        button_layout.addWidget(self.open_folder_button)
        main_layout.addLayout(button_layout)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Processing... %p%")
        main_layout.addWidget(self.progress_bar)

        # Log Group
        log_group = QGroupBox("📋 Log")
        log_layout = QVBoxLayout()
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFont(QFont("Courier New", 9))
        log_layout.addWidget(self.log_area)
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)

        # Store the last output directory
        self.last_output_dir = None

    @Slot()
    def browse_input_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select Input CSV", "", "CSV Files (*.csv);;All Files (*)"
        )
        if filepath:
            self.input_label.setText(filepath)
            # Automatically set output directory to the directory of the selected CSV file
            output_dir = os.path.dirname(filepath)
            self.output_label.setText(output_dir)
            self.last_output_dir = output_dir

    @Slot()
    def browse_output_directory(self):
        dirpath = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if dirpath:
            self.output_label.setText(dirpath)
            self.last_output_dir = dirpath

    @Slot()
    def open_output_folder(self):
        """Opens the output folder in the system file explorer."""
        if not self.last_output_dir or not os.path.exists(self.last_output_dir):
            QMessageBox.warning(
                self, "Warning",
                "Output directory not found. Please generate reports first."
            )
            return

        try:
            # Platform-specific folder opening
            if platform.system() == "Windows":
                os.startfile(self.last_output_dir)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", self.last_output_dir])
            else:  # Linux and others
                subprocess.run(["xdg-open", self.last_output_dir])
        except Exception as e:
            QMessageBox.warning(
                self, "Error",
                f"Could not open folder: {e}\n\nPath: {self.last_output_dir}"
            )

    @Slot()
    def start_report_generation(self):
        input_file = self.input_label.text()
        output_dir = self.output_label.text()

        # Validation
        if "Select" in input_file or not input_file or not os.path.exists(input_file):
            QMessageBox.warning(
                self, "⚠️  Warning",
                "Please select a valid input CSV file."
            )
            return
        if "Select" in output_dir or not output_dir:
            QMessageBox.warning(
                self, "⚠️  Warning",
                "Please select an output directory."
            )
            return

        # Store output directory
        self.last_output_dir = output_dir

        # Clear log and setup UI
        self.log_area.clear()
        self.log_area.append("🚀 Starting report generation...\n")
        self.generate_button.setEnabled(False)
        self.open_folder_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Initializing...")

        # Create worker thread
        self.thread = QThread()
        self.worker = Worker(input_file, output_dir, self.get_organization_option())
        self.worker.moveToThread(self.thread)

        # Connect signals
        self.worker.progress.connect(self.log_area.append)
        self.worker.conflict.connect(self.handle_conflict)
        self.worker.error.connect(self.handle_error)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.finished.connect(self.on_generation_complete)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

        # Pulse the progress bar
        self.progress_bar.setRange(0, 0)  # Indeterminate mode

    @Slot()
    def on_generation_complete(self):
        """Called when report generation is finished."""
        self.generate_button.setEnabled(True)
        self.open_folder_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 100)
        self.log_area.append("\n✅ Report generation complete!")

    def get_organization_option(self):
        if self.org_collection.isChecked():
            return "collection-date"
        if self.org_tested.isChecked():
            return "tested-date"
        if self.org_mrn.isChecked():
            return "mrn"
        return None

    @Slot(str, str, list)
    def handle_conflict(self, mrn, date_collected, sample_ids):
        """Handle conflict when multiple samples are found for same patient."""
        dialog = SelectSampleDialog(self, mrn, date_collected, sample_ids)
        if dialog.exec() == QDialog.Accepted:
            choice = dialog.get_selected_sample_index()
            self.worker.on_conflict_resolved(choice)
        else:
            self.worker.on_conflict_resolved(-1)  # Skipped

    @Slot(str, str)
    def handle_error(self, title, message):
        """Handle errors from the worker thread."""
        QMessageBox.critical(self, title, message)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())