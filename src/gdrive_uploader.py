"""Google Drive uploader module for sharing generated reports.

Provides functionality to upload files to Google Drive and share them with
specified email addresses. Uses Google Service Account authentication for
automated/server-side access.
"""
import os
from pathlib import Path
from typing import Tuple, Optional, List
from dataclasses import dataclass

# Google API imports - optional dependency
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False


# Required scopes for Drive access
SCOPES = ['https://www.googleapis.com/auth/drive.file']


@dataclass
class DriveConfig:
    """Configuration for Google Drive upload.

    Attributes:
        service_account_file: Path to service account JSON key file
        folder_id: Optional Google Drive folder ID to upload to (if None, uploads to root)
    """
    service_account_file: str
    folder_id: Optional[str] = None


class GoogleDriveUploader:
    """Handles uploading files to Google Drive and sharing them.

    This class provides functionality to upload files to Google Drive using
    a service account, and share them with specified email addresses. It's
    designed for automated upload of generated PDF reports.

    Prerequisites:
        1. Create a Google Cloud project
        2. Enable the Google Drive API
        3. Create a service account and download the JSON key file
        4. (For Workspace) Grant domain-wide delegation if needed

    Example:
        config = DriveConfig(
            service_account_file="/path/to/service-account.json",
            folder_id="your-folder-id"  # Optional
        )
        uploader = GoogleDriveUploader(config)
        success, result = uploader.upload_and_share(
            file_path="/path/to/report.pdf",
            share_emails=["user@example.com"]
        )
    """

    def __init__(self, config: DriveConfig):
        """Initialize the Google Drive uploader.

        Args:
            config: DriveConfig object with service account settings

        Raises:
            ImportError: If Google API libraries are not installed
        """
        if not GOOGLE_API_AVAILABLE:
            raise ImportError(
                "Google API libraries not installed. "
                "Install with: pip install google-api-python-client google-auth"
            )

        self.config = config
        self._service = None

    def authenticate(self) -> Tuple[bool, str]:
        """Authenticate with Google Drive API using service account.

        Returns:
            Tuple of (success, message)
        """
        try:
            if not os.path.exists(self.config.service_account_file):
                return False, f"Service account file not found: {self.config.service_account_file}"

            credentials = service_account.Credentials.from_service_account_file(
                self.config.service_account_file, scopes=SCOPES
            )
            self._service = build('drive', 'v3', credentials=credentials)
            return True, "Successfully authenticated with Google Drive API."

        except Exception as e:
            return False, f"Authentication failed: {type(e).__name__}: {e}"

    def test_connection(self) -> Tuple[bool, str]:
        """Test the Google Drive connection.

        Attempts to authenticate and list files to verify access.

        Returns:
            Tuple of (success, message)
        """
        success, message = self.authenticate()
        if not success:
            return success, message

        try:
            # Try to list files (limited to 1) to verify access
            self._service.files().list(pageSize=1, fields="files(id, name)").execute()
            return True, "Connection successful! Service account has access to Google Drive."
        except HttpError as e:
            return False, f"API error: {e}"
        except Exception as e:
            return False, f"Connection test failed: {type(e).__name__}: {e}"

    def _get_mime_type(self, file_path: str) -> str:
        """Get MIME type for a file based on extension.

        Args:
            file_path: Path to the file

        Returns:
            MIME type string
        """
        ext = Path(file_path).suffix.lower()
        mime_types = {
            '.pdf': 'application/pdf',
            '.csv': 'text/csv',
            '.txt': 'text/plain',
            '.json': 'application/json',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.xls': 'application/vnd.ms-excel',
        }
        return mime_types.get(ext, 'application/octet-stream')

    def upload_file(self, file_path: str, custom_name: Optional[str] = None) -> Tuple[bool, str]:
        """Upload a file to Google Drive.

        Args:
            file_path: Path to the file to upload
            custom_name: Optional custom name for the file in Drive

        Returns:
            Tuple of (success, file_id_or_error_message)
        """
        if self._service is None:
            success, message = self.authenticate()
            if not success:
                return False, message

        if not os.path.exists(file_path):
            return False, f"File not found: {file_path}"

        try:
            file_name = custom_name or Path(file_path).name
            mime_type = self._get_mime_type(file_path)

            file_metadata = {'name': file_name}
            if self.config.folder_id:
                file_metadata['parents'] = [self.config.folder_id]

            media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
            file = self._service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()

            return True, file.get('id')

        except HttpError as e:
            return False, f"Upload failed: {e}"
        except Exception as e:
            return False, f"Upload error: {type(e).__name__}: {e}"

    def share_file(self, file_id: str, email: str, role: str = 'reader') -> Tuple[bool, str]:
        """Share a file with an email address.

        Args:
            file_id: Google Drive file ID
            email: Email address to share with
            role: Permission role ('reader', 'writer', 'commenter')

        Returns:
            Tuple of (success, message)
        """
        if self._service is None:
            success, message = self.authenticate()
            if not success:
                return False, message

        try:
            permission = {
                'type': 'user',
                'role': role,
                'emailAddress': email
            }

            self._service.permissions().create(
                fileId=file_id,
                body=permission,
                sendNotificationEmail=True,
                fields='id'
            ).execute()

            return True, f"Successfully shared with {email}"

        except HttpError as e:
            # Check for specific errors
            if 'notFound' in str(e):
                return False, f"File not found: {file_id}"
            elif 'invalid' in str(e).lower() and 'email' in str(e).lower():
                return False, f"Invalid email address: {email}"
            return False, f"Share failed: {e}"
        except Exception as e:
            return False, f"Share error: {type(e).__name__}: {e}"

    def upload_and_share(
        self,
        file_path: str,
        share_emails: List[str],
        custom_name: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Upload a file and share it with multiple email addresses.

        Args:
            file_path: Path to the file to upload
            share_emails: List of email addresses to share with
            custom_name: Optional custom name for the file in Drive

        Returns:
            Tuple of (success, file_id_or_error_message)
        """
        # Upload file
        success, result = self.upload_file(file_path, custom_name)
        if not success:
            return False, result

        file_id = result

        # Share with each email
        share_errors = []
        share_successes = []

        for email in share_emails:
            share_success, share_message = self.share_file(file_id, email)
            if share_success:
                share_successes.append(email)
            else:
                share_errors.append(f"{email}: {share_message}")

        # Return result
        if share_errors:
            if share_successes:
                return True, (
                    f"File uploaded (ID: {file_id}). "
                    f"Shared with: {', '.join(share_successes)}. "
                    f"Failed to share with: {'; '.join(share_errors)}"
                )
            else:
                return True, (
                    f"File uploaded (ID: {file_id}) but sharing failed: {'; '.join(share_errors)}"
                )
        else:
            return True, f"File uploaded and shared successfully (ID: {file_id})"

    def upload_multiple_and_share(
        self,
        file_paths: List[str],
        share_emails: List[str],
        progress_callback: Optional[callable] = None
    ) -> Tuple[bool, str]:
        """Upload multiple files and share them with email addresses.

        Args:
            file_paths: List of file paths to upload
            share_emails: List of email addresses to share with
            progress_callback: Optional callback for progress updates

        Returns:
            Tuple of (all_success, summary_message)
        """
        if not file_paths:
            return False, "No files provided for upload"

        if not share_emails:
            return False, "No email addresses provided for sharing"

        successful_uploads = []
        failed_uploads = []

        for i, file_path in enumerate(file_paths, 1):
            file_name = Path(file_path).name
            if progress_callback:
                progress_callback(f"Uploading {i}/{len(file_paths)}: {file_name}")

            success, result = self.upload_and_share(file_path, share_emails)
            if success:
                successful_uploads.append(file_name)
            else:
                failed_uploads.append(f"{file_name}: {result}")

        # Build summary
        summary_parts = []
        if successful_uploads:
            summary_parts.append(f"Uploaded {len(successful_uploads)} file(s): {', '.join(successful_uploads)}")
        if failed_uploads:
            summary_parts.append(f"Failed {len(failed_uploads)} file(s): {'; '.join(failed_uploads)}")

        all_success = len(failed_uploads) == 0
        return all_success, " | ".join(summary_parts)


def create_drive_uploader_from_config(config_dict: dict) -> Optional[GoogleDriveUploader]:
    """Create a GoogleDriveUploader from a configuration dictionary.

    Args:
        config_dict: Dictionary containing Drive configuration keys:
            - gdrive_service_account_file: Path to service account JSON
            - gdrive_folder_id: Optional folder ID

    Returns:
        GoogleDriveUploader instance or None if configuration is incomplete
        or Google API is not available
    """
    if not GOOGLE_API_AVAILABLE:
        return None

    service_account_file = config_dict.get('gdrive_service_account_file')
    if not service_account_file:
        return None

    try:
        drive_config = DriveConfig(
            service_account_file=service_account_file,
            folder_id=config_dict.get('gdrive_folder_id')
        )
        return GoogleDriveUploader(drive_config)
    except Exception:
        return None


def is_google_api_available() -> bool:
    """Check if Google API libraries are installed.

    Returns:
        True if Google API is available, False otherwise
    """
    return GOOGLE_API_AVAILABLE
