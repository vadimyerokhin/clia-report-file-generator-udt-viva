# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pandas",
#     "pyside6",
#     "reportlab",
#     "google-api-python-client",
#     "google-auth",
# ]
# ///
"""GUI application for the CLIA Report Generator.

Provides a user-friendly interface for generating PDF laboratory reports
with integrated email and Google Drive upload capabilities.
"""
import sys
import os
import io
import subprocess
from typing import Optional
from PySide6.QtCore import QThread, Signal, Slot, QObject, QEventLoop, Qt, QDate, QTimer
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog, QGroupBox, QRadioButton,
    QTextEdit, QMessageBox, QDialog, QDialogButtonBox, QListWidget, QProgressBar,
    QCheckBox, QSpinBox, QTabWidget, QScrollArea, QFrame, QTableWidget,
    QTableWidgetItem, QHeaderView, QComboBox, QDateEdit, QAbstractItemView,
    QSplitter
)
from PySide6.QtGui import QFont, QColor

from .main import generate_reports, generate_positives_summary_pdf, run_post_generation_actions, create_zip_archive
from .run_summary import RunSummary
from .config import POSITIVES_SUMMARY_FILENAME
from .utils import open_file_explorer, validate_output_directory
from .exceptions import InvalidPathError
from .config_manager import ConfigManager
from .email_sender import create_email_sender_from_config
from .gdrive_uploader import is_google_api_available, create_drive_uploader_from_config
from . import db_search


STORE_LAB_RESULTS_SCRIPT = os.path.join(
    os.path.expanduser("~"), "Documents", "Projects", "scripts_misc", "store_lab_results.py"
)


def store_results_to_db(input_file, progress_callback=None):
    """Store results into the lab results database after report generation.

    Determines the Results folder from the input CSV path and invokes
    store_lab_results.py via subprocess. Failures are logged but never
    propagate — this must not break the main workflow.

    Args:
        input_file: Path to the export CSV used for report generation.
        progress_callback: Optional callable for progress messages.
    """
    if not os.path.isfile(STORE_LAB_RESULTS_SCRIPT):
        if progress_callback:
            progress_callback(f"  DB storage script not found: {STORE_LAB_RESULTS_SCRIPT}")
        return

    results_folder = os.path.dirname(os.path.abspath(input_file))

    # Sanity check: folder should exist and contain the input CSV
    if not os.path.isdir(results_folder):
        if progress_callback:
            progress_callback(f"  Results folder not found: {results_folder}")
        return

    try:
        result = subprocess.run(
            [sys.executable, STORE_LAB_RESULTS_SCRIPT, results_folder],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            # Extract key stats from output for the log
            for line in result.stdout.splitlines():
                line = line.strip()
                if line and ("IMPORTED" in line or "SKIPPED" in line
                             or "Patients:" in line or "Positives:" in line
                             or "Database:" in line or "Test results:" in line):
                    if progress_callback:
                        progress_callback(f"  {line}")
            if progress_callback:
                progress_callback("  Database storage complete.")
        else:
            if progress_callback:
                stderr_summary = (result.stderr or "").strip()[:200]
                progress_callback(f"  Database storage failed (exit {result.returncode}): {stderr_summary}")
    except subprocess.TimeoutExpired:
        if progress_callback:
            progress_callback("  Database storage timed out (60s limit).")
    except Exception as e:
        if progress_callback:
            progress_callback(f"  Database storage error: {e}")


class Worker(QObject):
    """Background worker for report generation."""
    finished = Signal()
    progress = Signal(str)
    progress_update = Signal(int, int)  # current, total
    conflict = Signal(str, str, list)
    error = Signal(str, str)  # title, message

    def __init__(self, input_file, output_dir, organize_by, config):
        super().__init__()
        self.input_file = input_file
        self.output_dir = output_dir
        self.organize_by = organize_by
        self.config = config
        self.summary = RunSummary()
        self.user_choice = -1
        self.conflict_loop = None

    def run(self):
        try:
            self.summary.set_output_stream(io.StringIO())

            def progress_callback(message):
                self.progress.emit(message)

            def progress_update_callback(current, total):
                self.progress_update.emit(current, total)

            def conflict_handler(mrn, date_collected, sample_ids):
                # Create an event loop to block this thread until user responds
                self.conflict_loop = QEventLoop()
                self.user_choice = -1

                # Emit signal to show dialog on main thread
                self.conflict.emit(mrn, date_collected, list(sample_ids))

                # Block this thread until user responds
                self.conflict_loop.exec()

                return self.user_choice

            generate_reports(
                self.input_file, self.output_dir, self.organize_by,
                self.summary, progress_callback, conflict_handler, progress_update_callback
            )

            # Generate the positives summary PDF
            try:
                generate_positives_summary_pdf(self.summary, self.output_dir)
                if self.summary.positive_results:
                    summary_path = os.path.join(self.output_dir, POSITIVES_SUMMARY_FILENAME)
                    self.progress.emit(f"\n✅ Positives summary PDF generated: {summary_path}")
            except Exception as e:
                self.progress.emit(f"\n⚠️  Error generating positives summary PDF: {e}")

            # Run post-generation actions (email, Google Drive)
            if self.config.get('email_enabled') or self.config.get('gdrive_enabled'):
                self.progress.emit("\n" + "="*40 + "\n📤 Post-Generation Actions\n" + "="*40)
                run_post_generation_actions(self.output_dir, self.config, progress_callback)

            # Create ZIP archive if enabled (runs independently of email/gdrive)
            if self.config.get('create_zip') and self.summary.pdfs_generated > 0:
                self.progress.emit("\n" + "="*40 + "\n🗜️  ZIP Archive\n" + "="*40)
                create_zip_archive(
                    self.input_file, self.output_dir, self.config, progress_callback
                )

            # Store results to lab database (always runs, failures are non-blocking)
            self.progress.emit("\n" + "="*40 + "\n💾 Database Storage\n" + "="*40)
            store_results_to_db(self.input_file, progress_callback)

            # Append summary to progress
            summary_output = self.summary.output_stream.getvalue()
            self.progress.emit("\n" + "="*40 + "\n📊 Run Summary\n" + "="*40)
            self.progress.emit(summary_output)

            # Success message
            if self.summary.pdfs_generated > 0:
                self.progress.emit(f"\n🎉 Successfully generated {self.summary.pdfs_generated} report(s)!")

        except (FileNotFoundError, PermissionError, OSError, IOError) as e:
            error_msg = f"File system error: {e}"
            self.error.emit("Error During Processing", error_msg)
            self.progress.emit(f"\n❌ Fatal error: {error_msg}")
        except Exception as e:
            error_msg = f"Unexpected error ({type(e).__name__}): {e}"
            self.error.emit("Error During Processing", error_msg)
            self.progress.emit(f"\n❌ Fatal error: {error_msg}")
        finally:
            self.finished.emit()

    @Slot(int)
    def on_conflict_resolved(self, choice):
        self.user_choice = choice
        # Quit the event loop to unblock the worker thread
        if self.conflict_loop and self.conflict_loop.isRunning():
            self.conflict_loop.quit()


class SelectSampleDialog(QDialog):
    """Dialog for selecting between multiple samples for the same patient."""
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


class EmailSettingsWidget(QWidget):
    """Widget for email settings configuration."""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        # Enable checkbox
        self.enable_checkbox = QCheckBox("Enable email sending for billing documents")
        layout.addWidget(self.enable_checkbox)

        # Settings frame
        self.settings_frame = QFrame()
        settings_layout = QVBoxLayout(self.settings_frame)

        # SMTP Server
        smtp_layout = QHBoxLayout()
        smtp_layout.addWidget(QLabel("SMTP Server:"))
        self.smtp_server = QLineEdit()
        self.smtp_server.setPlaceholderText("e.g., smtp.gmail.com")
        smtp_layout.addWidget(self.smtp_server)
        settings_layout.addLayout(smtp_layout)

        # SMTP Port
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("SMTP Port:"))
        self.smtp_port = QSpinBox()
        self.smtp_port.setRange(1, 65535)
        self.smtp_port.setValue(587)
        port_layout.addWidget(self.smtp_port)
        port_layout.addStretch()
        settings_layout.addLayout(port_layout)

        # Username
        user_layout = QHBoxLayout()
        user_layout.addWidget(QLabel("Username:"))
        self.username = QLineEdit()
        self.username.setPlaceholderText("Email address for SMTP authentication")
        user_layout.addWidget(self.username)
        settings_layout.addLayout(user_layout)

        # Password
        pass_layout = QHBoxLayout()
        pass_layout.addWidget(QLabel("Password:"))
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setPlaceholderText("App password (for Gmail, use App Password)")
        pass_layout.addWidget(self.password)
        settings_layout.addLayout(pass_layout)

        # Recipient
        recipient_layout = QHBoxLayout()
        recipient_layout.addWidget(QLabel("Send to:"))
        self.recipient = QLineEdit()
        self.recipient.setPlaceholderText("Billing department email address")
        recipient_layout.addWidget(self.recipient)
        settings_layout.addLayout(recipient_layout)

        # Test button
        test_layout = QHBoxLayout()
        self.test_button = QPushButton("Test Connection")
        self.test_button.clicked.connect(self.test_connection)
        test_layout.addWidget(self.test_button)
        self.test_status = QLabel("")
        test_layout.addWidget(self.test_status)
        test_layout.addStretch()
        settings_layout.addLayout(test_layout)

        layout.addWidget(self.settings_frame)

        # Note about app passwords
        note = QLabel(
            "<i>Note: For Gmail, use an App Password instead of your regular password. "
            "Go to Google Account → Security → 2-Step Verification → App passwords.</i>"
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(note)

        layout.addStretch()

        # Connect enable checkbox
        self.enable_checkbox.toggled.connect(self.settings_frame.setEnabled)
        self.settings_frame.setEnabled(False)

    def test_connection(self):
        """Test the SMTP connection."""
        self.test_status.setText("Testing...")
        self.test_status.setStyleSheet("")
        QApplication.processEvents()

        config = self.get_config()
        sender = create_email_sender_from_config(config)

        if sender is None:
            self.test_status.setText("❌ Incomplete configuration")
            self.test_status.setStyleSheet("color: red;")
            return

        success, message = sender.test_connection()

        if success:
            self.test_status.setText("✅ Connection successful!")
            self.test_status.setStyleSheet("color: green;")
        else:
            self.test_status.setText(f"❌ {message[:50]}...")
            self.test_status.setStyleSheet("color: red;")
            QMessageBox.warning(self, "Connection Failed", message)

    def get_config(self):
        """Get email configuration as dictionary."""
        return {
            'email_enabled': self.enable_checkbox.isChecked(),
            'email_smtp_server': self.smtp_server.text().strip(),
            'email_smtp_port': self.smtp_port.value(),
            'email_username': self.username.text().strip(),
            'email_password': self.password.text().strip(),
            'email_recipient': self.recipient.text().strip(),
            'email_use_tls': True
        }

    def set_config(self, config):
        """Set email configuration from dictionary."""
        self.enable_checkbox.setChecked(config.get('email_enabled', False))
        self.smtp_server.setText(config.get('email_smtp_server', ''))
        self.smtp_port.setValue(config.get('email_smtp_port', 587))
        self.username.setText(config.get('email_username', ''))
        self.password.setText(config.get('email_password', '').strip())
        self.recipient.setText(config.get('email_recipient', ''))


class GoogleDriveSettingsWidget(QWidget):
    """Widget for Google Drive settings configuration."""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        # Check if Google API is available
        if not is_google_api_available():
            unavailable_label = QLabel(
                "<b>Google Drive integration is not available.</b><br><br>"
                "The required Google API libraries are not installed.<br>"
                "To enable Google Drive upload, install the dependencies:<br><br>"
                "<code>pip install google-api-python-client google-auth</code>"
            )
            unavailable_label.setWordWrap(True)
            layout.addWidget(unavailable_label)
            layout.addStretch()
            self.enable_checkbox = None
            return

        # Enable checkbox
        self.enable_checkbox = QCheckBox("Enable Google Drive upload for generated reports")
        layout.addWidget(self.enable_checkbox)

        # Settings frame
        self.settings_frame = QFrame()
        settings_layout = QVBoxLayout(self.settings_frame)

        # Service account file
        sa_layout = QHBoxLayout()
        sa_layout.addWidget(QLabel("Service Account:"))
        self.service_account_file = QLineEdit()
        self.service_account_file.setPlaceholderText("Path to service account JSON file")
        self.service_account_file.setReadOnly(True)
        sa_layout.addWidget(self.service_account_file)
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self.browse_service_account)
        sa_layout.addWidget(self.browse_button)
        settings_layout.addLayout(sa_layout)

        # Folder ID (optional)
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("Folder ID:"))
        self.folder_id = QLineEdit()
        self.folder_id.setPlaceholderText("Optional: Google Drive folder ID to upload to")
        folder_layout.addWidget(self.folder_id)
        settings_layout.addLayout(folder_layout)

        # Share emails
        settings_layout.addWidget(QLabel("Share with emails:"))
        self.share_emails_list = QListWidget()
        self.share_emails_list.setMaximumHeight(100)
        settings_layout.addWidget(self.share_emails_list)

        email_add_layout = QHBoxLayout()
        self.new_email = QLineEdit()
        self.new_email.setPlaceholderText("Enter email address")
        email_add_layout.addWidget(self.new_email)
        self.add_email_button = QPushButton("Add")
        self.add_email_button.clicked.connect(self.add_share_email)
        email_add_layout.addWidget(self.add_email_button)
        self.remove_email_button = QPushButton("Remove")
        self.remove_email_button.clicked.connect(self.remove_share_email)
        email_add_layout.addWidget(self.remove_email_button)
        settings_layout.addLayout(email_add_layout)

        # Test button
        test_layout = QHBoxLayout()
        self.test_button = QPushButton("Test Connection")
        self.test_button.clicked.connect(self.test_connection)
        test_layout.addWidget(self.test_button)
        self.test_status = QLabel("")
        test_layout.addWidget(self.test_status)
        test_layout.addStretch()
        settings_layout.addLayout(test_layout)

        layout.addWidget(self.settings_frame)

        # Setup instructions
        note = QLabel(
            "<i>Setup: 1) Create a Google Cloud project, 2) Enable Drive API, "
            "3) Create a service account, 4) Download the JSON key file. "
            "For Workspace: Grant domain-wide delegation if needed.</i>"
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(note)

        layout.addStretch()

        # Connect enable checkbox
        self.enable_checkbox.toggled.connect(self.settings_frame.setEnabled)
        self.settings_frame.setEnabled(False)

    def browse_service_account(self):
        """Browse for service account JSON file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select Service Account JSON", "", "JSON Files (*.json);;All Files (*)"
        )
        if filepath:
            self.service_account_file.setText(filepath)

    def add_share_email(self):
        """Add email to share list."""
        email = self.new_email.text().strip()
        if email and '@' in email:
            # Check for duplicates
            for i in range(self.share_emails_list.count()):
                if self.share_emails_list.item(i).text() == email:
                    return
            self.share_emails_list.addItem(email)
            self.new_email.clear()

    def remove_share_email(self):
        """Remove selected email from share list."""
        current = self.share_emails_list.currentRow()
        if current >= 0:
            self.share_emails_list.takeItem(current)

    def test_connection(self):
        """Test the Google Drive connection."""
        self.test_status.setText("Testing...")
        self.test_status.setStyleSheet("")
        QApplication.processEvents()

        config = self.get_config()
        uploader = create_drive_uploader_from_config(config)

        if uploader is None:
            self.test_status.setText("❌ Incomplete configuration")
            self.test_status.setStyleSheet("color: red;")
            return

        success, message = uploader.test_connection()

        if success:
            self.test_status.setText("✅ Connection successful!")
            self.test_status.setStyleSheet("color: green;")
        else:
            self.test_status.setText(f"❌ {message[:50]}...")
            self.test_status.setStyleSheet("color: red;")
            QMessageBox.warning(self, "Connection Failed", message)

    def get_config(self):
        """Get Google Drive configuration as dictionary."""
        if self.enable_checkbox is None:
            return {
                'gdrive_enabled': False,
                'gdrive_service_account_file': '',
                'gdrive_folder_id': '',
                'gdrive_share_emails': []
            }

        share_emails = []
        for i in range(self.share_emails_list.count()):
            share_emails.append(self.share_emails_list.item(i).text())

        return {
            'gdrive_enabled': self.enable_checkbox.isChecked(),
            'gdrive_service_account_file': self.service_account_file.text().strip(),
            'gdrive_folder_id': self.folder_id.text().strip(),
            'gdrive_share_emails': share_emails
        }

    def set_config(self, config):
        """Set Google Drive configuration from dictionary."""
        if not self.enable_checkbox:
            return  # Google API not available

        self.enable_checkbox.setChecked(config.get('gdrive_enabled', False))
        self.service_account_file.setText(config.get('gdrive_service_account_file', ''))
        self.folder_id.setText(config.get('gdrive_folder_id', ''))

        self.share_emails_list.clear()
        for email in config.get('gdrive_share_emails', []):
            self.share_emails_list.addItem(email)


class _SearchWorker(QObject):
    """Background worker for database search queries."""
    finished = Signal(list, int)  # results, total_count
    error = Signal(str)

    def __init__(self, query, date_from, date_to, test_name, test_result,
                 dob, collected_by, limit, offset):
        super().__init__()
        self.query = query
        self.date_from = date_from
        self.date_to = date_to
        self.test_name = test_name
        self.test_result = test_result
        self.dob = dob
        self.collected_by = collected_by
        self.limit = limit
        self.offset = offset

    def run(self):
        try:
            results, total = db_search.search_patients(
                query=self.query,
                date_from=self.date_from,
                date_to=self.date_to,
                test_name=self.test_name,
                test_result=self.test_result,
                dob=self.dob,
                collected_by=self.collected_by,
                limit=self.limit,
                offset=self.offset,
            )
            self.finished.emit(results, total)
        except FileNotFoundError:
            self.error.emit("Database not found. Generate reports first to populate the database.")
        except Exception as e:
            self.error.emit(str(e))


class DatabaseSearchWidget(QWidget):
    """Widget for searching the lab results database."""

    RESULTS_PER_PAGE = 100
    COLUMNS = ["Name", "MRN", "DOB", "Collection Date", "# Tests", "# Positive"]

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self._current_results: list = []
        self._total_count = 0
        self._current_offset = 0
        self._search_thread = None
        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(300)
        self._debounce_timer.timeout.connect(self._execute_search)

        self._build_ui()
        self._check_db_status()

    # ── UI Construction ─────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Reports directory selector
        dir_group = QGroupBox("Reports Directory")
        dir_layout = QHBoxLayout(dir_group)
        self.reports_dir_input = QLineEdit()
        self.reports_dir_input.setPlaceholderText(
            "Directory where generated reports are stored (for opening PDFs)"
        )
        self.reports_dir_input.setToolTip(
            "Set the root folder where your generated PDF reports and billing files are stored. "
            "The app searches this folder recursively when you click 'Open Report'."
        )
        saved_dir = self.config_manager.get("search_reports_directory", "")
        if saved_dir and os.path.isdir(saved_dir):
            self.reports_dir_input.setText(saved_dir)
        elif not saved_dir:
            # Default to output dir from report generation tab
            fallback = self.config_manager.get("last_output_dir", "")
            if fallback and os.path.isdir(fallback):
                self.reports_dir_input.setText(fallback)
        self.reports_dir_browse = QPushButton("Browse...")
        self.reports_dir_browse.clicked.connect(self._browse_reports_dir)
        dir_layout.addWidget(QLabel("Path:"))
        dir_layout.addWidget(self.reports_dir_input)
        dir_layout.addWidget(self.reports_dir_browse)
        layout.addWidget(dir_group)

        # Quick search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by patient name or MRN...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.returnPressed.connect(self._execute_search)
        self.search_input.textChanged.connect(self._on_search_text_changed)
        search_layout.addWidget(self.search_input)

        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self._execute_search)
        search_layout.addWidget(self.search_button)

        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self._clear_search)
        search_layout.addWidget(self.clear_button)
        layout.addLayout(search_layout)

        # Advanced filters (collapsible)
        self.filter_group = QGroupBox("Advanced Filters")
        self.filter_group.setCheckable(True)
        self.filter_group.setChecked(False)
        filter_layout = QVBoxLayout(self.filter_group)

        # Row 1: Date range
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("Collection Date From:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setSpecialValueText("Any")
        self.date_from.setDate(self.date_from.minimumDate())
        date_layout.addWidget(self.date_from)
        date_layout.addWidget(QLabel("To:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setSpecialValueText("Any")
        self.date_to.setDate(self.date_to.minimumDate())
        date_layout.addWidget(self.date_to)
        date_layout.addStretch()
        filter_layout.addLayout(date_layout)

        # Row 2: Test name, result, DOB
        row2_layout = QHBoxLayout()
        row2_layout.addWidget(QLabel("Test Name:"))
        self.test_name_combo = QComboBox()
        self.test_name_combo.setEditable(True)
        self.test_name_combo.addItem("")  # "Any" placeholder
        self.test_name_combo.setMinimumWidth(150)
        row2_layout.addWidget(self.test_name_combo)

        row2_layout.addWidget(QLabel("Result:"))
        self.result_combo = QComboBox()
        self.result_combo.addItems(["", "Positive", "Negative", "Pending"])
        row2_layout.addWidget(self.result_combo)

        row2_layout.addWidget(QLabel("DOB:"))
        self.dob_edit = QDateEdit()
        self.dob_edit.setCalendarPopup(True)
        self.dob_edit.setSpecialValueText("Any")
        self.dob_edit.setDate(self.dob_edit.minimumDate())
        row2_layout.addWidget(self.dob_edit)
        row2_layout.addStretch()
        filter_layout.addLayout(row2_layout)

        # Row 3: Collected by
        row3_layout = QHBoxLayout()
        row3_layout.addWidget(QLabel("Collected By:"))
        self.collected_by_input = QLineEdit()
        self.collected_by_input.setPlaceholderText("Provider name...")
        row3_layout.addWidget(self.collected_by_input)
        row3_layout.addStretch()
        filter_layout.addLayout(row3_layout)

        layout.addWidget(self.filter_group)

        # Status / DB info bar
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        # Splitter for results table and detail panel
        splitter = QSplitter(Qt.Vertical)

        # Results table
        results_widget = QWidget()
        results_layout = QVBoxLayout(results_widget)
        results_layout.setContentsMargins(0, 0, 0, 0)

        self.results_count_label = QLabel("")
        results_layout.addWidget(self.results_count_label)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(len(self.COLUMNS))
        self.results_table.setHorizontalHeaderLabels(self.COLUMNS)
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, len(self.COLUMNS)):
            self.results_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.results_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.results_table.setSortingEnabled(True)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.currentItemChanged.connect(self._on_row_selected)
        results_layout.addWidget(self.results_table)

        # Load more button
        self.load_more_button = QPushButton("Load More Results")
        self.load_more_button.setVisible(False)
        self.load_more_button.clicked.connect(self._load_more)
        results_layout.addWidget(self.load_more_button)

        splitter.addWidget(results_widget)

        # Detail panel
        detail_widget = QWidget()
        detail_layout = QVBoxLayout(detail_widget)
        detail_layout.setContentsMargins(0, 0, 0, 0)

        detail_header = QHBoxLayout()
        self.detail_label = QLabel("Select a row above to view test details")
        self.detail_label.setStyleSheet("font-weight: bold;")
        detail_header.addWidget(self.detail_label)
        detail_header.addStretch()

        self.open_pdf_button = QPushButton("Open Report PDF")
        self.open_pdf_button.setEnabled(False)
        self.open_pdf_button.clicked.connect(self._open_report_pdf)
        detail_header.addWidget(self.open_pdf_button)

        self.open_billing_button = QPushButton("Open Billing File")
        self.open_billing_button.setEnabled(False)
        self.open_billing_button.clicked.connect(self._open_billing_file)
        detail_header.addWidget(self.open_billing_button)

        self.open_folder_button = QPushButton("Open Folder")
        self.open_folder_button.setEnabled(False)
        self.open_folder_button.clicked.connect(self._open_containing_folder)
        detail_header.addWidget(self.open_folder_button)

        detail_layout.addLayout(detail_header)

        self.detail_table = QTableWidget()
        self.detail_table.setColumnCount(5)
        self.detail_table.setHorizontalHeaderLabels(
            ["Test Name", "Result", "Units", "Flags", "Completed"]
        )
        self.detail_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 5):
            self.detail_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.detail_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.detail_table.verticalHeader().setVisible(False)
        detail_layout.addWidget(self.detail_table)

        splitter.addWidget(detail_widget)
        splitter.setSizes([400, 200])

        layout.addWidget(splitter)

    # ── Database Status ─────────────────────────────────────────

    def _check_db_status(self):
        """Check if the database exists and update UI accordingly."""
        if not db_search.db_exists():
            self.status_label.setText(
                "No database found at: " + str(db_search.get_db_path()) +
                "\nGenerate reports first to populate the database."
            )
            self.status_label.setStyleSheet("color: orange; padding: 4px;")
            self.search_input.setEnabled(False)
            self.search_button.setEnabled(False)
            self.filter_group.setEnabled(False)
            return

        self.status_label.setText("Database: " + str(db_search.get_db_path()))
        self.status_label.setStyleSheet("color: gray; font-size: 10px;")
        self.search_input.setEnabled(True)
        self.search_button.setEnabled(True)
        self.filter_group.setEnabled(True)
        self._populate_test_names()

    def _populate_test_names(self):
        """Populate the test name combobox from the database."""
        try:
            names = db_search.get_distinct_test_names()
            self.test_name_combo.clear()
            self.test_name_combo.addItem("")  # "Any"
            self.test_name_combo.addItems(names)
        except Exception:
            pass  # Non-critical

    # ── Reports Directory ───────────────────────────────────────

    def _browse_reports_dir(self):
        dirpath = QFileDialog.getExistingDirectory(self, "Select Reports Directory")
        if dirpath:
            self.reports_dir_input.setText(dirpath)
            self.config_manager.set("search_reports_directory", dirpath)
            self.config_manager.save_config()

    def _get_reports_dir(self) -> str:
        """Get the current reports directory, with validation."""
        d = self.reports_dir_input.text().strip()
        if d and os.path.isdir(d):
            return d
        # Fallback to output dir
        fallback = self.config_manager.get("last_output_dir", "")
        if fallback and os.path.isdir(fallback):
            return fallback
        return ""

    # ── Search Execution ────────────────────────────────────────

    def _on_search_text_changed(self):
        """Debounce text input to avoid querying on every keystroke."""
        self._debounce_timer.start()

    def _clear_search(self):
        """Clear all search fields and results."""
        self.search_input.clear()
        self.date_from.setDate(self.date_from.minimumDate())
        self.date_to.setDate(self.date_to.minimumDate())
        self.test_name_combo.setCurrentIndex(0)
        self.result_combo.setCurrentIndex(0)
        self.dob_edit.setDate(self.dob_edit.minimumDate())
        self.collected_by_input.clear()
        self.results_table.setRowCount(0)
        self.detail_table.setRowCount(0)
        self.results_count_label.setText("")
        self.detail_label.setText("Select a row above to view test details")
        self.load_more_button.setVisible(False)
        self._current_results = []
        self._total_count = 0
        self._current_offset = 0
        self._disable_action_buttons()

    def _execute_search(self, load_more=False):
        """Run the search query in a background thread."""
        if not db_search.db_exists():
            self._check_db_status()
            return

        # Prevent concurrent searches
        if self._search_thread and self._search_thread.isRunning():
            return

        if not load_more:
            self._current_offset = 0
            self._current_results = []

        # Gather filter values
        query = self.search_input.text().strip()

        date_from_str = ""
        if self.filter_group.isChecked() and self.date_from.date() != self.date_from.minimumDate():
            date_from_str = self.date_from.date().toString("yyyy-MM-dd")

        date_to_str = ""
        if self.filter_group.isChecked() and self.date_to.date() != self.date_to.minimumDate():
            date_to_str = self.date_to.date().toString("yyyy-MM-dd")

        test_name = ""
        if self.filter_group.isChecked():
            test_name = self.test_name_combo.currentText().strip()

        test_result = ""
        if self.filter_group.isChecked():
            test_result = self.result_combo.currentText().strip()

        dob_str = ""
        if self.filter_group.isChecked() and self.dob_edit.date() != self.dob_edit.minimumDate():
            dob_str = self.dob_edit.date().toString("yyyy-MM-dd")

        collected_by = ""
        if self.filter_group.isChecked():
            collected_by = self.collected_by_input.text().strip()

        # Don't search if everything is empty
        if not any([query, date_from_str, date_to_str, test_name, test_result, dob_str, collected_by]):
            if not load_more:
                self.results_count_label.setText("Enter a search term or apply filters.")
            return

        self.search_button.setEnabled(False)
        self.results_count_label.setText("Searching...")

        self._search_thread = QThread()
        worker = _SearchWorker(
            query, date_from_str, date_to_str, test_name, test_result,
            dob_str, collected_by, self.RESULTS_PER_PAGE, self._current_offset
        )
        worker.moveToThread(self._search_thread)
        self._search_thread.started.connect(worker.run)
        worker.finished.connect(self._on_search_complete)
        worker.error.connect(self._on_search_error)
        worker.finished.connect(self._search_thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.error.connect(self._search_thread.quit)
        worker.error.connect(worker.deleteLater)
        self._search_thread.finished.connect(self._search_thread.deleteLater)
        self._search_thread.start()

    @Slot(list, int)
    def _on_search_complete(self, results, total_count):
        """Handle search results from the background thread."""
        self.search_button.setEnabled(True)
        self._total_count = total_count

        if self._current_offset == 0:
            self._current_results = results
        else:
            self._current_results.extend(results)

        self._current_offset += len(results)
        self._populate_results_table()

        # Update count label
        showing = len(self._current_results)
        if total_count == 0:
            self.results_count_label.setText("No results found.")
        else:
            self.results_count_label.setText(
                f"Showing {showing} of {total_count} result(s)"
            )

        # Show/hide load more
        self.load_more_button.setVisible(showing < total_count)

    @Slot(str)
    def _on_search_error(self, message):
        """Handle search errors."""
        self.search_button.setEnabled(True)
        self.results_count_label.setText(f"Error: {message}")
        self.results_count_label.setStyleSheet("color: red;")

    def _load_more(self):
        """Load the next page of results."""
        self._execute_search(load_more=True)

    # ── Results Table ───────────────────────────────────────────

    def _populate_results_table(self):
        """Fill the results table with current results."""
        self.results_table.setSortingEnabled(False)
        self.results_table.setRowCount(len(self._current_results))

        for row_idx, result in enumerate(self._current_results):
            self.results_table.setItem(row_idx, 0, QTableWidgetItem(result["patient_name"]))
            self.results_table.setItem(row_idx, 1, QTableWidgetItem(result["mrn"]))
            self.results_table.setItem(row_idx, 2, QTableWidgetItem(
                self._format_date_display(result["dob"])
            ))
            self.results_table.setItem(row_idx, 3, QTableWidgetItem(
                self._format_date_display(result["collection_date"])
            ))

            tests_item = QTableWidgetItem()
            tests_item.setData(Qt.DisplayRole, result["num_tests"])
            self.results_table.setItem(row_idx, 4, tests_item)

            pos_item = QTableWidgetItem()
            pos_item.setData(Qt.DisplayRole, result["num_positive"])
            if result["num_positive"] > 0:
                pos_item.setForeground(QColor("red"))
            self.results_table.setItem(row_idx, 5, pos_item)

        self.results_table.setSortingEnabled(True)

    @staticmethod
    def _format_date_display(iso_date: str) -> str:
        """Convert ISO date to MM/DD/YYYY for display."""
        if not iso_date or len(iso_date) < 10:
            return iso_date or ""
        try:
            parts = iso_date[:10].split("-")
            return f"{parts[1]}/{parts[2]}/{parts[0]}"
        except (IndexError, ValueError):
            return iso_date

    # ── Detail Panel ────────────────────────────────────────────

    def _on_row_selected(self, current, _previous):
        """When a results row is selected, populate the detail panel."""
        if current is None:
            return

        row = current.row()
        if row < 0 or row >= len(self._current_results):
            return

        result = self._current_results[row]
        specimen_id = result["specimen_id"]

        self.detail_label.setText(
            f"Test details for {result['patient_name']} "
            f"(MRN: {result['mrn']}, Collected: {self._format_date_display(result['collection_date'])})"
        )

        try:
            details = db_search.get_specimen_details(specimen_id)
        except Exception as e:
            self.detail_label.setText(f"Error loading details: {e}")
            self.detail_table.setRowCount(0)
            self._disable_action_buttons()
            return

        self.detail_table.setRowCount(len(details))
        for i, test in enumerate(details):
            self.detail_table.setItem(i, 0, QTableWidgetItem(test.get("test_name", "")))

            result_text = test.get("result", "")
            result_item = QTableWidgetItem(result_text)
            if test.get("is_positive"):
                result_item.setForeground(QColor("red"))
            elif test.get("is_pending"):
                result_item.setForeground(QColor("orange"))
            self.detail_table.setItem(i, 1, result_item)

            self.detail_table.setItem(i, 2, QTableWidgetItem(test.get("units", "") or ""))
            self.detail_table.setItem(i, 3, QTableWidgetItem(test.get("flags", "") or ""))
            self.detail_table.setItem(i, 4, QTableWidgetItem(
                self._format_date_display(test.get("test_completed_at", "") or "")
            ))

        # Enable action buttons
        self.open_pdf_button.setEnabled(True)
        self.open_billing_button.setEnabled(True)
        self.open_folder_button.setEnabled(True)

    def _disable_action_buttons(self):
        self.open_pdf_button.setEnabled(False)
        self.open_billing_button.setEnabled(False)
        self.open_folder_button.setEnabled(False)

    def _get_selected_result(self) -> Optional[dict]:
        """Get the currently selected search result, or None."""
        row = self.results_table.currentRow()
        if row < 0 or row >= len(self._current_results):
            return None
        return self._current_results[row]

    # ── File Actions ────────────────────────────────────────────

    def _open_report_pdf(self):
        result = self._get_selected_result()
        if not result:
            return

        reports_dir = self._get_reports_dir()
        if not reports_dir:
            QMessageBox.warning(
                self, "Reports Directory Not Set",
                "Please set the reports directory at the top of this tab, "
                "then try again."
            )
            return

        matches = db_search.find_report_pdf(
            reports_dir,
            result["first_name"],
            result["last_name"],
            result["mrn"],
            result["collection_date"],
        )

        if not matches:
            QMessageBox.information(
                self, "Report Not Found",
                f"No PDF report found for {result['patient_name']} "
                f"(MRN: {result['mrn']}, Date: {result['collection_date']}).\n\n"
                f"The file may have been moved, deleted, or not yet generated.\n"
                f"Searched in: {reports_dir}"
            )
            return

        if len(matches) == 1:
            filepath = matches[0]
        else:
            # Multiple matches - let user choose
            dialog = QDialog(self)
            dialog.setWindowTitle("Multiple Reports Found")
            dialog.setMinimumWidth(500)
            dlayout = QVBoxLayout(dialog)
            dlayout.addWidget(QLabel("Multiple matching reports found. Select one to open:"))
            file_list = QListWidget()
            for m in matches:
                file_list.addItem(m)
            file_list.setCurrentRow(0)
            dlayout.addWidget(file_list)
            buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            dlayout.addWidget(buttons)
            if dialog.exec() != QDialog.Accepted:
                return
            filepath = matches[file_list.currentRow()]

        err = db_search.open_file(filepath)
        if err:
            QMessageBox.warning(self, "Error", err)

    def _open_billing_file(self):
        result = self._get_selected_result()
        if not result:
            return

        reports_dir = self._get_reports_dir()
        if not reports_dir:
            QMessageBox.warning(
                self, "Reports Directory Not Set",
                "Please set the reports directory at the top of this tab."
            )
            return

        matches = db_search.find_billing_files(
            reports_dir, result["mrn"], result["collection_date"]
        )

        if not matches:
            QMessageBox.information(
                self, "Billing File Not Found",
                f"No billing file found containing MRN {result['mrn']}.\n\n"
                f"Searched in: {reports_dir}"
            )
            return

        filepath = matches[0]
        if len(matches) > 1:
            dialog = QDialog(self)
            dialog.setWindowTitle("Multiple Billing Files Found")
            dialog.setMinimumWidth(500)
            dlayout = QVBoxLayout(dialog)
            dlayout.addWidget(QLabel("Multiple matching billing files found. Select one:"))
            file_list = QListWidget()
            for m in matches:
                file_list.addItem(m)
            file_list.setCurrentRow(0)
            dlayout.addWidget(file_list)
            buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            dlayout.addWidget(buttons)
            if dialog.exec() != QDialog.Accepted:
                return
            filepath = matches[file_list.currentRow()]

        err = db_search.open_file(filepath)
        if err:
            QMessageBox.warning(self, "Error", err)

    def _open_containing_folder(self):
        result = self._get_selected_result()
        if not result:
            return

        reports_dir = self._get_reports_dir()
        if not reports_dir:
            QMessageBox.warning(
                self, "Reports Directory Not Set",
                "Please set the reports directory at the top of this tab."
            )
            return

        # Try to find the PDF first, then open its parent folder
        matches = db_search.find_report_pdf(
            reports_dir,
            result["first_name"],
            result["last_name"],
            result["mrn"],
            result["collection_date"],
        )

        if matches:
            folder = os.path.dirname(matches[0])
        else:
            # Fall back to reports root
            folder = reports_dir

        from .utils import open_file_explorer
        err = open_file_explorer(folder)
        if err:
            QMessageBox.warning(self, "Error", err)

    # ── Persistence ─────────────────────────────────────────────

    def save_reports_dir(self):
        """Save the reports directory to config (called by MainWindow on close)."""
        d = self.reports_dir_input.text().strip()
        if d:
            self.config_manager.set("search_reports_directory", d)


class MainWindow(QMainWindow):
    """Main application window."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🧪 PDF Laboratory Report Generator")
        self.setGeometry(100, 100, 1000, 800)
        self.setMinimumSize(800, 600)

        # Initialize config manager
        self.config_manager = ConfigManager()
        self.load_settings()

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # Create tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # Main tab
        main_tab = QWidget()
        main_tab_layout = QVBoxLayout(main_tab)
        self._setup_main_tab(main_tab_layout)
        self.tab_widget.addTab(main_tab, "📄 Report Generation")

        # Email settings tab
        self.email_widget = EmailSettingsWidget()
        self.tab_widget.addTab(self.email_widget, "📧 Email Settings")

        # Google Drive settings tab
        self.gdrive_widget = GoogleDriveSettingsWidget()
        self.tab_widget.addTab(self.gdrive_widget, "☁️ Google Drive Settings")

        # Search tab
        self.search_widget = DatabaseSearchWidget(self.config_manager)
        self.tab_widget.addTab(self.search_widget, "🔍 Search Database")

        # Load settings into widgets
        self.apply_settings_to_widgets()

        # Store the last output directory
        self.last_output_dir = None

    def _setup_main_tab(self, layout):
        """Setup the main report generation tab."""
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
        layout.addWidget(file_group)

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
        layout.addWidget(org_group)

        # Post-generation info
        post_gen_group = QGroupBox("📤 Post-Generation Actions (Configure in other tabs)")
        post_gen_layout = QVBoxLayout()

        status_row = QHBoxLayout()
        self.email_status_label = QLabel("📧 Email: Disabled")
        self.gdrive_status_label = QLabel("☁️ Google Drive: Disabled")
        status_row.addWidget(self.email_status_label)
        status_row.addWidget(self.gdrive_status_label)
        status_row.addStretch()
        post_gen_layout.addLayout(status_row)

        self.create_zip_checkbox = QCheckBox("Create ZIP archive of patient reports (placed beside input CSV)")
        self.create_zip_checkbox.setChecked(True)
        self.create_zip_checkbox.setToolTip(
            "Creates a timestamped reports_YYYYMMDD_HHMMSS.zip in the same folder as the input CSV.\n"
            "Includes all patient PDFs (preserving organization structure).\n"
            "Excludes: positives_summary.pdf, billing CSV, and the original import CSV."
        )
        post_gen_layout.addWidget(self.create_zip_checkbox)

        post_gen_group.setLayout(post_gen_layout)
        layout.addWidget(post_gen_group)

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
        layout.addLayout(button_layout)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Processing... %p%")
        layout.addWidget(self.progress_bar)

        # Log Group
        log_group = QGroupBox("📋 Log")
        log_layout = QVBoxLayout()
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFont(QFont("Courier New", 9))
        log_layout.addWidget(self.log_area)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

    def load_settings(self):
        """Load settings from configuration manager."""
        self.settings = self.config_manager.load_config()

    def apply_settings_to_widgets(self):
        """Apply loaded settings to UI widgets."""
        # Apply organization option
        org = self.settings.get('organization_option', 'none')
        if org == 'collection-date':
            self.org_collection.setChecked(True)
        elif org == 'tested-date':
            self.org_tested.setChecked(True)
        elif org == 'mrn':
            self.org_mrn.setChecked(True)
        else:
            self.org_none.setChecked(True)

        # Apply last used paths
        last_input = self.settings.get('last_input_file', '')
        if last_input and os.path.exists(last_input):
            self.input_label.setText(last_input)

        last_output = self.settings.get('last_output_dir', '')
        if last_output and os.path.exists(last_output):
            self.output_label.setText(last_output)
            self.last_output_dir = last_output

        # Apply email settings
        self.email_widget.set_config(self.settings)

        # Apply Google Drive settings
        self.gdrive_widget.set_config(self.settings)

        # Apply ZIP setting
        self.create_zip_checkbox.setChecked(self.settings.get('create_zip', True))

        # Update status labels
        self.update_post_gen_status()

    def save_settings(self):
        """Save current settings to configuration manager."""
        # Get organization option
        if self.org_collection.isChecked():
            org = 'collection-date'
        elif self.org_tested.isChecked():
            org = 'tested-date'
        elif self.org_mrn.isChecked():
            org = 'mrn'
        else:
            org = 'none'

        self.settings['organization_option'] = org

        # Get paths
        input_file = self.input_label.text()
        if input_file and os.path.exists(input_file):
            self.settings['last_input_file'] = input_file

        output_dir = self.output_label.text()
        if output_dir and os.path.exists(output_dir):
            self.settings['last_output_dir'] = output_dir

        # Get email settings
        self.settings.update(self.email_widget.get_config())

        # Get Google Drive settings
        self.settings.update(self.gdrive_widget.get_config())

        # Get ZIP setting
        self.settings['create_zip'] = self.create_zip_checkbox.isChecked()

        # Save to file
        self.config_manager.save_config(self.settings)

    def update_post_gen_status(self):
        """Update the post-generation status labels."""
        email_config = self.email_widget.get_config()
        if email_config.get('email_enabled'):
            recipient = email_config.get('email_recipient', '')
            if recipient:
                self.email_status_label.setText(f"📧 Email: Enabled → {recipient}")
                self.email_status_label.setStyleSheet("color: green;")
            else:
                self.email_status_label.setText("📧 Email: Enabled (no recipient)")
                self.email_status_label.setStyleSheet("color: orange;")
        else:
            self.email_status_label.setText("📧 Email: Disabled")
            self.email_status_label.setStyleSheet("")

        gdrive_config = self.gdrive_widget.get_config()
        if gdrive_config.get('gdrive_enabled'):
            emails = gdrive_config.get('gdrive_share_emails', [])
            if emails:
                self.gdrive_status_label.setText(f"☁️ Google Drive: Enabled → {len(emails)} recipient(s)")
                self.gdrive_status_label.setStyleSheet("color: green;")
            else:
                self.gdrive_status_label.setText("☁️ Google Drive: Enabled (no recipients)")
                self.gdrive_status_label.setStyleSheet("color: orange;")
        else:
            self.gdrive_status_label.setText("☁️ Google Drive: Disabled")
            self.gdrive_status_label.setStyleSheet("")

    def closeEvent(self, event):
        """Save settings when window is closed."""
        self.search_widget.save_reports_dir()
        self.save_settings()
        super().closeEvent(event)

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

        error = open_file_explorer(self.last_output_dir)
        if error:
            QMessageBox.warning(
                self, "Error",
                f"{error}\n\nPath: {self.last_output_dir}"
            )

    def get_full_config(self):
        """Get complete configuration including all settings."""
        config = {}
        config.update(self.email_widget.get_config())
        config.update(self.gdrive_widget.get_config())
        config['create_zip'] = self.create_zip_checkbox.isChecked()
        return config

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

        # Validate output directory for write permissions
        try:
            validate_output_directory(output_dir)
        except InvalidPathError as e:
            QMessageBox.critical(
                self, "❌ Invalid Output Directory",
                f"The selected output directory is invalid or not writable:\n\n{e}"
            )
            return

        # Store output directory and save settings
        self.last_output_dir = output_dir
        self.save_settings()

        # Update post-gen status
        self.update_post_gen_status()

        # Clear log and setup UI
        self.log_area.clear()
        self.log_area.append("🚀 Starting report generation...\n")
        self.generate_button.setEnabled(False)
        self.open_folder_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Initializing...")

        # Get full configuration for post-generation actions
        config = self.get_full_config()

        # Create worker thread
        self.thread = QThread()
        self.worker = Worker(input_file, output_dir, self.get_organization_option(), config)
        self.worker.moveToThread(self.thread)

        # Connect signals
        self.worker.progress.connect(self.log_area.append)
        self.worker.progress_update.connect(self.update_progress_bar)
        self.worker.conflict.connect(self.handle_conflict)
        self.worker.error.connect(self.handle_error)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.finished.connect(self.on_generation_complete)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    @Slot(int, int)
    def update_progress_bar(self, current, total):
        """Updates the progress bar with current progress."""
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(percentage)
            self.progress_bar.setFormat(f"Processing report {current} of {total} ({percentage}%)")

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


def main():
    """Main entry point for the GUI application."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
