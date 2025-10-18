# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pandas",
#     "pyside6",
#     "reportlab",
# ]
# ///
import sys
import io
from PySide6.QtCore import QThread, Signal, Slot, QObject
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog, QGroupBox, QRadioButton,
    QTextEdit, QMessageBox, QDialog, QDialogButtonBox, QListWidget
)
from main import generate_reports
from run_summary import RunSummary

class Worker(QObject):
    finished = Signal()
    progress = Signal(str)
    conflict = Signal(str, str, list)
    conflict_resolved = Signal(int)

    def __init__(self, input_file, output_dir, organize_by):
        super().__init__()
        self.input_file = input_file
        self.output_dir = output_dir
        self.organize_by = organize_by
        self.summary = RunSummary()
        self.user_choice = -1

    def run(self):
        self.summary.set_output_stream(io.StringIO())

        def progress_callback(message):
            self.progress.emit(message)

        def conflict_handler(mrn, date_collected, sample_ids):
            self.conflict.emit(mrn, date_collected, list(sample_ids))
            # Block until the main thread provides the resolution
            return self.user_choice

        generate_reports(self.input_file, self.output_dir, self.organize_by, self.summary, progress_callback, conflict_handler)

        # Append summary to progress
        summary_output = self.summary.output_stream.getvalue()
        self.progress.emit("\n" + "="*30 + "\nRun Summary\n" + "="*30)
        self.progress.emit(summary_output)
        self.finished.emit()

    @Slot(int)
    def on_conflict_resolved(self, choice):
        self.user_choice = choice

class SelectSampleDialog(QDialog):
    def __init__(self, parent, mrn, date_collected, sample_ids):
        super().__init__(parent)
        self.setWindowTitle("Conflict: Multiple Samples Found")
        self.layout = QVBoxLayout(self)
        message = QLabel(f"Multiple samples found for MR# {mrn} on {date_collected}.\nPlease select one to continue or cancel to skip.")
        self.layout.addWidget(message)
        self.sample_list = QListWidget()
        for sample_id in sample_ids:
            self.sample_list.addItem(f"Sample ID: {sample_id}")
        self.layout.addWidget(self.sample_list)
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def get_selected_sample_index(self):
        return self.sample_list.currentRow()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF Laboratory Report Generator")
        self.setGeometry(100, 100, 800, 600)
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        file_group = QGroupBox("File Selection")
        file_layout = QVBoxLayout()
        input_layout = QHBoxLayout()
        self.input_label = QLineEdit("Select input CSV file...")
        self.input_label.setReadOnly(True)
        self.input_button = QPushButton("Browse...")
        self.input_button.clicked.connect(self.browse_input_file)
        input_layout.addWidget(self.input_label)
        input_layout.addWidget(self.input_button)
        file_layout.addLayout(input_layout)
        output_layout = QHBoxLayout()
        self.output_label = QLineEdit("Select output directory...")
        self.output_label.setReadOnly(True)
        self.output_button = QPushButton("Browse...")
        self.output_button.clicked.connect(self.browse_output_directory)
        output_layout.addWidget(self.output_label)
        output_layout.addWidget(self.output_button)
        file_layout.addLayout(output_layout)
        file_group.setLayout(file_layout)
        main_layout.addWidget(file_group)

        org_group = QGroupBox("Report Organization")
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

        self.generate_button = QPushButton("Generate Reports")
        self.generate_button.clicked.connect(self.start_report_generation)
        main_layout.addWidget(self.generate_button)

        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout()
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        log_layout.addWidget(self.log_area)
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)

    @Slot()
    def browse_input_file(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Select Input CSV", "", "CSV Files (*.csv)")
        if filepath:
            self.input_label.setText(filepath)

    @Slot()
    def browse_output_directory(self):
        dirpath = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if dirpath:
            self.output_label.setText(dirpath)

    @Slot()
    def start_report_generation(self):
        input_file = self.input_label.text()
        output_dir = self.output_label.text()

        if "Select" in input_file or not input_file:
            QMessageBox.warning(self, "Warning", "Please select an input file.")
            return
        if "Select" in output_dir or not output_dir:
            QMessageBox.warning(self, "Warning", "Please select an output directory.")
            return

        self.log_area.clear()
        self.log_area.append("Starting report generation...")
        self.generate_button.setEnabled(False)

        self.thread = QThread()
        self.worker = Worker(input_file, output_dir, self.get_organization_option())
        self.worker.moveToThread(self.thread)

        self.worker.progress.connect(self.log_area.append)
        self.worker.conflict.connect(self.handle_conflict)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(lambda: self.generate_button.setEnabled(True))
        self.thread.start()

    def get_organization_option(self):
        if self.org_collection.isChecked(): return "collection-date"
        if self.org_tested.isChecked(): return "tested-date"
        if self.org_mrn.isChecked(): return "mrn"
        return None

    @Slot(str, str, list)
    def handle_conflict(self, mrn, date_collected, sample_ids):
        dialog = SelectSampleDialog(self, mrn, date_collected, sample_ids)
        if dialog.exec() == QDialog.Accepted:
            choice = dialog.get_selected_sample_index()
            self.worker.on_conflict_resolved(choice)
        else:
            self.worker.on_conflict_resolved(-1) # Skipped

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())