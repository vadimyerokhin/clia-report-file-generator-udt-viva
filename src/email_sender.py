"""Email sender module for sending billing documents via SMTP.

Provides functionality to send emails with attachments using configurable
SMTP settings. Designed for sending billing CSV files after report generation.
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from pathlib import Path
from typing import Tuple, Optional, List
from dataclasses import dataclass


@dataclass
class EmailConfig:
    """Configuration for email sending.

    Attributes:
        smtp_server: SMTP server hostname (e.g., "smtp.gmail.com")
        smtp_port: SMTP server port (e.g., 587 for TLS)
        username: SMTP authentication username (typically email address)
        password: SMTP authentication password (use app password for Gmail)
        sender_email: Email address to send from (usually same as username)
        use_tls: Whether to use STARTTLS encryption (default True)
    """
    smtp_server: str
    smtp_port: int
    username: str
    password: str
    sender_email: Optional[str] = None
    use_tls: bool = True

    def __post_init__(self):
        """Set sender_email to username if not provided."""
        if self.sender_email is None:
            self.sender_email = self.username


class EmailSender:
    """Handles sending emails with attachments via SMTP.

    This class provides a simple interface for sending emails with file
    attachments using SMTP. It supports TLS encryption and is designed
    to work with common email providers like Gmail, Outlook, etc.

    Example:
        config = EmailConfig(
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            username="your-email@gmail.com",
            password="your-app-password"
        )
        sender = EmailSender(config)
        success, message = sender.send_email(
            to_email="recipient@example.com",
            subject="Billing Document",
            body="Please find attached the billing document.",
            attachment_path="/path/to/billing.csv"
        )
    """

    def __init__(self, config: EmailConfig):
        """Initialize the email sender with configuration.

        Args:
            config: EmailConfig object with SMTP settings
        """
        self.config = config

    def test_connection(self) -> Tuple[bool, str]:
        """Test the SMTP connection without sending an email.

        Returns:
            Tuple of (success, message) where success is True if connection
            was successful, and message contains details or error info.
        """
        try:
            context = ssl.create_default_context()

            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port, timeout=10) as server:
                if self.config.use_tls:
                    server.starttls(context=context)
                server.login(self.config.username, self.config.password)

            return True, "Connection successful! SMTP server is reachable and credentials are valid."

        except smtplib.SMTPAuthenticationError as e:
            return False, f"Authentication failed: {e}. Check username and password (use app password for Gmail)."
        except smtplib.SMTPConnectError as e:
            return False, f"Connection failed: {e}. Check server address and port."
        except smtplib.SMTPServerDisconnected as e:
            return False, f"Server disconnected: {e}. The server may require different settings."
        except TimeoutError:
            return False, "Connection timed out. Check server address and network connectivity."
        except Exception as e:
            return False, f"Connection error: {type(e).__name__}: {e}"

    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        attachment_paths: Optional[List[str]] = None
    ) -> Tuple[bool, str]:
        """Send an email with optional attachments.

        Args:
            to_email: Recipient email address
            subject: Email subject line
            body: Email body text (plain text)
            attachment_paths: Optional list of file paths to attach

        Returns:
            Tuple of (success, message) where success is True if email was
            sent successfully, and message contains details or error info.
        """
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.config.sender_email
            msg['To'] = to_email
            msg['Subject'] = subject

            # Add body
            msg.attach(MIMEText(body, 'plain'))

            # Add attachments
            if attachment_paths:
                for attachment_path in attachment_paths:
                    path = Path(attachment_path)
                    if not path.exists():
                        return False, f"Attachment not found: {attachment_path}"

                    try:
                        with open(path, 'rb') as f:
                            attachment = MIMEApplication(f.read(), Name=path.name)
                        attachment['Content-Disposition'] = f'attachment; filename="{path.name}"'
                        msg.attach(attachment)
                    except (IOError, OSError) as e:
                        return False, f"Error reading attachment {path.name}: {e}"

            # Send email
            context = ssl.create_default_context()

            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port, timeout=30) as server:
                if self.config.use_tls:
                    server.starttls(context=context)
                server.login(self.config.username, self.config.password)
                server.send_message(msg)

            attachment_info = ""
            if attachment_paths:
                attachment_names = [Path(p).name for p in attachment_paths]
                attachment_info = f" with {len(attachment_paths)} attachment(s): {', '.join(attachment_names)}"

            return True, f"Email sent successfully to {to_email}{attachment_info}."

        except smtplib.SMTPAuthenticationError as e:
            return False, f"Authentication failed: {e}"
        except smtplib.SMTPRecipientsRefused as e:
            return False, f"Recipient refused: {e}. Check the recipient email address."
        except smtplib.SMTPSenderRefused as e:
            return False, f"Sender refused: {e}. Check your sender email address."
        except smtplib.SMTPDataError as e:
            return False, f"Data error: {e}. The email may be too large or contain invalid content."
        except smtplib.SMTPException as e:
            return False, f"SMTP error: {e}"
        except TimeoutError:
            return False, "Email send timed out. Check network connectivity."
        except Exception as e:
            return False, f"Error sending email: {type(e).__name__}: {e}"

    def send_billing_document(
        self,
        to_email: str,
        billing_file_path: str,
        run_date: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Convenience method to send a billing document.

        Creates an appropriate subject and body for billing documents.

        Args:
            to_email: Recipient email address
            billing_file_path: Path to the billing CSV file
            run_date: Optional date string for the subject line

        Returns:
            Tuple of (success, message)
        """
        from datetime import datetime

        if run_date is None:
            run_date = datetime.now().strftime("%Y-%m-%d")

        subject = f"CLIA Lab Report - Billing Document - {run_date}"
        body = f"""Dear Billing Department,

Please find attached the billing document (CPT 80307) generated on {run_date}.

This document contains patient billing information for urine drug testing services.

Best regards,
CLIA Report Generator
"""

        return self.send_email(to_email, subject, body, [billing_file_path])


def create_email_sender_from_config(config_dict: dict) -> Optional[EmailSender]:
    """Create an EmailSender from a configuration dictionary.

    Args:
        config_dict: Dictionary containing email configuration keys:
            - email_smtp_server
            - email_smtp_port
            - email_username
            - email_password
            - email_sender (optional)
            - email_use_tls (optional, default True)

    Returns:
        EmailSender instance or None if configuration is incomplete
    """
    required_keys = ['email_smtp_server', 'email_smtp_port', 'email_username', 'email_password']

    for key in required_keys:
        if not config_dict.get(key):
            return None

    try:
        email_config = EmailConfig(
            smtp_server=config_dict['email_smtp_server'].strip(),
            smtp_port=int(config_dict['email_smtp_port']),
            username=config_dict['email_username'].strip(),
            password=config_dict['email_password'].strip(),
            sender_email=config_dict.get('email_sender'),
            use_tls=config_dict.get('email_use_tls', True)
        )
        return EmailSender(email_config)
    except (ValueError, TypeError):
        return None
