# utils/brevo_email.py
import logging
from django.conf import settings
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from threading import Thread

logger = logging.getLogger(__name__)

class BrevoEmailSender:
    """
    Brevo API email sender that works on Render.com and other platforms
    that block SMTP ports.
    """
    
    def __init__(self):
        # Configure API key authorization
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = settings.BREVO_API_KEY
        
        # Create API instance
        self.api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(configuration)
        )
        
        logger.info("Brevo API email sender initialized")
    
    def send_email(self, subject, to_emails, text_content=None, html_content=None, from_email=None, from_name=None):
        """
        Send email using Brevo API.
        
        Args:
            subject: Email subject
            to_emails: List of recipient email addresses
            text_content: Plain text content
            html_content: HTML content
            from_email: Sender email (must be verified in Brevo)
            from_name: Sender name
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Prepare sender
            sender = {
                "email": from_email or settings.DEFAULT_FROM_EMAIL,
                "name": from_name or "FrameStack"
            }
            
            # Prepare recipients
            to = [{"email": email} for email in to_emails]
            
            # Create SendSmtpEmail object
            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                to=to,
                sender=sender,
                subject=subject,
                html_content=html_content or f"<p>{text_content}</p>",
                text_content=text_content or "This email requires HTML support."
            )
            
            # Send the email
            api_response = self.api_instance.send_transac_email(send_smtp_email)
            
            logger.info(f"[SUCCESS] Email sent via Brevo API to {to_emails}. Message ID: {api_response.message_id}")
            return True
            
        except ApiException as e:
            logger.error(f"[ERROR] Brevo API error: {e}")
            return False
        except Exception as e:
            logger.error(f"[ERROR] Unexpected error sending email: {str(e)}")
            return False

# Create a singleton instance
brevo_email_sender = BrevoEmailSender()

def send_email_async_api(subject, message, recipient_list, html_message=None, from_email=None):
    """
    Drop-in replacement for the SMTP send_email_async function.
    Uses Brevo API instead of SMTP.
    """
    def _send():
        try:
            success = brevo_email_sender.send_email(
                subject=subject,
                to_emails=recipient_list,
                text_content=message,
                html_content=html_message,
                from_email=from_email
            )
            
            if success:
                logger.info(f"[SUCCESS] Email queued for delivery to {recipient_list}")
            else:
                logger.error(f"[ERROR] Failed to queue email to {recipient_list}")
                
        except Exception as e:
            logger.error(f"[ERROR] Exception in email thread: {str(e)}")
    
    # Run in background thread
    thread = Thread(target=_send)
    thread.daemon = True
    thread.start()