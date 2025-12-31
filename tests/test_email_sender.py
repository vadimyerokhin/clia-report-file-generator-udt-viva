"""Tests for the email_sender module."""
import unittest
import tempfile
import os
from unittest.mock import patch, MagicMock, mock_open

from src.email_sender import (
    EmailConfig,
    EmailSender,
    create_email_sender_from_config
)


class TestEmailConfig(unittest.TestCase):
    """Test suite for EmailConfig dataclass."""

    def test_basic_config_creation(self):
        """Test basic EmailConfig creation."""
        config = EmailConfig(
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            username="test@gmail.com",
            password="test_password"
        )
        self.assertEqual(config.smtp_server, "smtp.gmail.com")
        self.assertEqual(config.smtp_port, 587)
        self.assertEqual(config.username, "test@gmail.com")
        self.assertEqual(config.password, "test_password")
        self.assertEqual(config.sender_email, "test@gmail.com")  # Should default to username
        self.assertTrue(config.use_tls)

    def test_config_with_sender_email(self):
        """Test EmailConfig with custom sender email."""
        config = EmailConfig(
            smtp_server="smtp.example.com",
            smtp_port=465,
            username="user@example.com",
            password="password",
            sender_email="noreply@example.com",
            use_tls=False
        )
        self.assertEqual(config.sender_email, "noreply@example.com")
        self.assertFalse(config.use_tls)


class TestEmailSender(unittest.TestCase):
    """Test suite for EmailSender class."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = EmailConfig(
            smtp_server="smtp.test.com",
            smtp_port=587,
            username="test@test.com",
            password="test_password"
        )
        self.sender = EmailSender(self.config)

    @patch('src.email_sender.smtplib.SMTP')
    def test_test_connection_success(self, mock_smtp):
        """Test successful SMTP connection test."""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        success, message = self.sender.test_connection()

        self.assertTrue(success)
        self.assertIn("successful", message.lower())
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("test@test.com", "test_password")

    @patch('src.email_sender.smtplib.SMTP')
    def test_test_connection_auth_failure(self, mock_smtp):
        """Test SMTP connection with authentication failure."""
        import smtplib
        mock_smtp.return_value.__enter__ = MagicMock()
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
        mock_smtp.return_value.__enter__.return_value.login.side_effect = \
            smtplib.SMTPAuthenticationError(535, b"Authentication failed")

        success, message = self.sender.test_connection()

        self.assertFalse(success)
        self.assertIn("authentication", message.lower())

    @patch('src.email_sender.smtplib.SMTP')
    def test_test_connection_timeout(self, mock_smtp):
        """Test SMTP connection timeout."""
        mock_smtp.side_effect = TimeoutError("Connection timed out")

        success, message = self.sender.test_connection()

        self.assertFalse(success)
        self.assertIn("timed out", message.lower())

    @patch('src.email_sender.smtplib.SMTP')
    def test_send_email_success(self, mock_smtp):
        """Test successful email sending."""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        success, message = self.sender.send_email(
            to_email="recipient@example.com",
            subject="Test Subject",
            body="Test body content"
        )

        self.assertTrue(success)
        self.assertIn("successfully", message.lower())
        mock_server.send_message.assert_called_once()

    @patch('src.email_sender.smtplib.SMTP')
    def test_send_email_with_attachment(self, mock_smtp):
        """Test email sending with attachment."""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("test,data\n1,2")
            temp_file = f.name

        try:
            success, message = self.sender.send_email(
                to_email="recipient@example.com",
                subject="Test with Attachment",
                body="Test body",
                attachment_paths=[temp_file]
            )

            self.assertTrue(success)
            self.assertIn("attachment", message.lower())
        finally:
            os.unlink(temp_file)

    def test_send_email_attachment_not_found(self):
        """Test email sending with non-existent attachment."""
        success, message = self.sender.send_email(
            to_email="recipient@example.com",
            subject="Test",
            body="Test",
            attachment_paths=["/nonexistent/file.csv"]
        )

        self.assertFalse(success)
        self.assertIn("not found", message.lower())

    @patch('src.email_sender.smtplib.SMTP')
    def test_send_billing_document(self, mock_smtp):
        """Test sending billing document."""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        # Create a temporary billing file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("Patient,CPT,Date\nDoe,80307,2024-01-15")
            temp_file = f.name

        try:
            success, message = self.sender.send_billing_document(
                to_email="billing@hospital.com",
                billing_file_path=temp_file,
                run_date="2024-01-15"
            )

            self.assertTrue(success)
        finally:
            os.unlink(temp_file)


class TestCreateEmailSenderFromConfig(unittest.TestCase):
    """Test suite for create_email_sender_from_config function."""

    def test_valid_config(self):
        """Test creation with valid config dictionary."""
        config_dict = {
            'email_smtp_server': 'smtp.gmail.com',
            'email_smtp_port': 587,
            'email_username': 'user@gmail.com',
            'email_password': 'password123'
        }

        sender = create_email_sender_from_config(config_dict)

        self.assertIsNotNone(sender)
        self.assertIsInstance(sender, EmailSender)

    def test_missing_required_fields(self):
        """Test creation with missing required fields."""
        config_dict = {
            'email_smtp_server': 'smtp.gmail.com',
            'email_smtp_port': 587
            # Missing username and password
        }

        sender = create_email_sender_from_config(config_dict)

        self.assertIsNone(sender)

    def test_empty_config(self):
        """Test creation with empty config."""
        sender = create_email_sender_from_config({})

        self.assertIsNone(sender)

    def test_invalid_port(self):
        """Test creation with invalid port."""
        config_dict = {
            'email_smtp_server': 'smtp.gmail.com',
            'email_smtp_port': 'not_a_number',
            'email_username': 'user@gmail.com',
            'email_password': 'password'
        }

        sender = create_email_sender_from_config(config_dict)

        self.assertIsNone(sender)


if __name__ == '__main__':
    unittest.main()
