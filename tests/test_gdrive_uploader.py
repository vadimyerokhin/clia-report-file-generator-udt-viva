"""Tests for the gdrive_uploader module."""
import unittest
import tempfile
import os
from unittest.mock import patch, MagicMock

from src.gdrive_uploader import (
    DriveConfig,
    GoogleDriveUploader,
    create_drive_uploader_from_config,
    is_google_api_available,
    GOOGLE_API_AVAILABLE
)


class TestDriveConfig(unittest.TestCase):
    """Test suite for DriveConfig dataclass."""

    def test_basic_config_creation(self):
        """Test basic DriveConfig creation."""
        config = DriveConfig(
            service_account_file="/path/to/service-account.json"
        )
        self.assertEqual(config.service_account_file, "/path/to/service-account.json")
        self.assertIsNone(config.folder_id)

    def test_config_with_folder_id(self):
        """Test DriveConfig with folder ID."""
        config = DriveConfig(
            service_account_file="/path/to/sa.json",
            folder_id="1234567890abcdef"
        )
        self.assertEqual(config.folder_id, "1234567890abcdef")


class TestIsGoogleApiAvailable(unittest.TestCase):
    """Test suite for is_google_api_available function."""

    def test_api_availability(self):
        """Test that is_google_api_available returns correct value."""
        result = is_google_api_available()
        self.assertEqual(result, GOOGLE_API_AVAILABLE)


@unittest.skipUnless(GOOGLE_API_AVAILABLE, "Google API libraries not installed")
class TestGoogleDriveUploader(unittest.TestCase):
    """Test suite for GoogleDriveUploader class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary "service account" file
        self.temp_dir = tempfile.mkdtemp()
        self.sa_file = os.path.join(self.temp_dir, "service-account.json")
        with open(self.sa_file, 'w') as f:
            f.write('{"type": "service_account", "project_id": "test"}')

        self.config = DriveConfig(
            service_account_file=self.sa_file
        )
        self.uploader = GoogleDriveUploader(self.config)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('src.gdrive_uploader.service_account.Credentials.from_service_account_file')
    @patch('src.gdrive_uploader.build')
    def test_authenticate_success(self, mock_build, mock_credentials):
        """Test successful authentication."""
        mock_creds = MagicMock()
        mock_credentials.return_value = mock_creds
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        success, message = self.uploader.authenticate()

        self.assertTrue(success)
        self.assertIn("authenticated", message.lower())
        mock_credentials.assert_called_once()
        mock_build.assert_called_once()

    def test_authenticate_file_not_found(self):
        """Test authentication with missing service account file."""
        config = DriveConfig(service_account_file="/nonexistent/path.json")
        uploader = GoogleDriveUploader(config)

        success, message = uploader.authenticate()

        self.assertFalse(success)
        self.assertIn("not found", message.lower())

    @patch('src.gdrive_uploader.service_account.Credentials.from_service_account_file')
    @patch('src.gdrive_uploader.build')
    def test_test_connection_success(self, mock_build, mock_credentials):
        """Test successful connection test."""
        mock_creds = MagicMock()
        mock_credentials.return_value = mock_creds
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Mock the files().list() call
        mock_service.files.return_value.list.return_value.execute.return_value = {
            'files': []
        }

        success, message = self.uploader.test_connection()

        self.assertTrue(success)
        self.assertIn("successful", message.lower())

    @patch('src.gdrive_uploader.service_account.Credentials.from_service_account_file')
    @patch('src.gdrive_uploader.build')
    def test_upload_file_success(self, mock_build, mock_credentials):
        """Test successful file upload."""
        mock_creds = MagicMock()
        mock_credentials.return_value = mock_creds
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Mock the files().create() call
        mock_service.files.return_value.create.return_value.execute.return_value = {
            'id': 'new_file_id_123'
        }

        # Create a test file
        test_file = os.path.join(self.temp_dir, "test.pdf")
        with open(test_file, 'wb') as f:
            f.write(b"PDF content")

        success, result = self.uploader.upload_file(test_file)

        self.assertTrue(success)
        self.assertEqual(result, 'new_file_id_123')

    def test_upload_file_not_found(self):
        """Test upload with non-existent file."""
        # Authenticate first
        self.uploader._service = MagicMock()

        success, result = self.uploader.upload_file("/nonexistent/file.pdf")

        self.assertFalse(success)
        self.assertIn("not found", result.lower())

    @patch('src.gdrive_uploader.service_account.Credentials.from_service_account_file')
    @patch('src.gdrive_uploader.build')
    def test_share_file_success(self, mock_build, mock_credentials):
        """Test successful file sharing."""
        mock_creds = MagicMock()
        mock_credentials.return_value = mock_creds
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Mock the permissions().create() call
        mock_service.permissions.return_value.create.return_value.execute.return_value = {
            'id': 'permission_id'
        }

        success, message = self.uploader.share_file("file_id_123", "user@example.com")

        self.assertTrue(success)
        self.assertIn("shared", message.lower())

    @patch('src.gdrive_uploader.service_account.Credentials.from_service_account_file')
    @patch('src.gdrive_uploader.build')
    def test_upload_and_share_success(self, mock_build, mock_credentials):
        """Test upload and share in one operation."""
        mock_creds = MagicMock()
        mock_credentials.return_value = mock_creds
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Mock the files().create() call
        mock_service.files.return_value.create.return_value.execute.return_value = {
            'id': 'new_file_id'
        }
        # Mock the permissions().create() call
        mock_service.permissions.return_value.create.return_value.execute.return_value = {
            'id': 'permission_id'
        }

        # Create a test file
        test_file = os.path.join(self.temp_dir, "test.pdf")
        with open(test_file, 'wb') as f:
            f.write(b"PDF content")

        success, result = self.uploader.upload_and_share(
            test_file,
            ["user1@example.com", "user2@example.com"]
        )

        self.assertTrue(success)
        self.assertIn("new_file_id", result)

    @patch('src.gdrive_uploader.service_account.Credentials.from_service_account_file')
    @patch('src.gdrive_uploader.build')
    def test_upload_multiple_and_share(self, mock_build, mock_credentials):
        """Test uploading multiple files."""
        mock_creds = MagicMock()
        mock_credentials.return_value = mock_creds
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Mock the files().create() call
        mock_service.files.return_value.create.return_value.execute.return_value = {
            'id': 'file_id'
        }
        # Mock the permissions().create() call
        mock_service.permissions.return_value.create.return_value.execute.return_value = {
            'id': 'permission_id'
        }

        # Create test files
        test_files = []
        for i in range(3):
            test_file = os.path.join(self.temp_dir, f"test{i}.pdf")
            with open(test_file, 'wb') as f:
                f.write(b"PDF content")
            test_files.append(test_file)

        progress_messages = []
        success, message = self.uploader.upload_multiple_and_share(
            test_files,
            ["user@example.com"],
            progress_callback=progress_messages.append
        )

        self.assertTrue(success)
        self.assertIn("3", message)  # Should mention 3 files
        self.assertGreater(len(progress_messages), 0)

    def test_upload_multiple_no_files(self):
        """Test upload with empty file list."""
        success, message = self.uploader.upload_multiple_and_share([], ["user@example.com"])

        self.assertFalse(success)
        self.assertIn("no files", message.lower())

    def test_upload_multiple_no_emails(self):
        """Test upload with empty email list."""
        test_file = os.path.join(self.temp_dir, "test.pdf")
        with open(test_file, 'wb') as f:
            f.write(b"content")

        success, message = self.uploader.upload_multiple_and_share([test_file], [])

        self.assertFalse(success)
        self.assertIn("no email", message.lower())

    def test_get_mime_type(self):
        """Test MIME type detection."""
        self.assertEqual(self.uploader._get_mime_type("file.pdf"), "application/pdf")
        self.assertEqual(self.uploader._get_mime_type("file.csv"), "text/csv")
        self.assertEqual(self.uploader._get_mime_type("file.txt"), "text/plain")
        self.assertEqual(self.uploader._get_mime_type("file.unknown"), "application/octet-stream")


@unittest.skipUnless(GOOGLE_API_AVAILABLE, "Google API libraries not installed")
class TestCreateDriveUploaderFromConfig(unittest.TestCase):
    """Test suite for create_drive_uploader_from_config function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.sa_file = os.path.join(self.temp_dir, "service-account.json")
        with open(self.sa_file, 'w') as f:
            f.write('{"type": "service_account"}')

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_valid_config(self):
        """Test creation with valid config dictionary."""
        config_dict = {
            'gdrive_service_account_file': self.sa_file,
            'gdrive_folder_id': 'folder_id_123'
        }

        uploader = create_drive_uploader_from_config(config_dict)

        self.assertIsNotNone(uploader)
        self.assertIsInstance(uploader, GoogleDriveUploader)

    def test_missing_service_account_file(self):
        """Test creation with missing service account file path."""
        config_dict = {
            'gdrive_folder_id': 'folder_id_123'
        }

        uploader = create_drive_uploader_from_config(config_dict)

        self.assertIsNone(uploader)

    def test_empty_config(self):
        """Test creation with empty config."""
        uploader = create_drive_uploader_from_config({})

        self.assertIsNone(uploader)


class TestGoogleDriveUploaderWithoutAPI(unittest.TestCase):
    """Test suite for GoogleDriveUploader when API is not available."""

    @patch('src.gdrive_uploader.GOOGLE_API_AVAILABLE', False)
    def test_create_uploader_without_api(self):
        """Test that uploader returns None when API is not available."""
        # Need to reimport to get the patched value
        from src.gdrive_uploader import create_drive_uploader_from_config

        with patch('src.gdrive_uploader.GOOGLE_API_AVAILABLE', False):
            uploader = create_drive_uploader_from_config({
                'gdrive_service_account_file': '/path/to/file.json'
            })
            # Since GOOGLE_API_AVAILABLE is True at module load time,
            # we test that an incomplete config returns None
            self.assertIsNone(uploader)


if __name__ == '__main__':
    unittest.main()
