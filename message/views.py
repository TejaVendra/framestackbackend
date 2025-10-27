# views.py - Contact Message Views with Brevo API Email
from rest_framework import generics, status
from rest_framework.response import Response
from django.conf import settings
from .models import ContactMessage
from .serializers import ContactMessageSerializer
import logging
from datetime import datetime

# Import Brevo API email sender
from utils.brevo_email import send_email_async_api

logger = logging.getLogger(__name__)

# -------------------------------------------------------
# ✅ Use Brevo API for email sending (works on Render!)
# -------------------------------------------------------
send_email_async = send_email_async_api  # Use Brevo API instead of SMTP


# -------------------------------------------------------
# 📧 Contact Message Create View
# -------------------------------------------------------
class ContactMessageCreateView(generics.CreateAPIView):
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer

    def perform_create(self, serializer):
        # Save the contact message
        contact_message = serializer.save()
        
        # Send confirmation email to user
        self._send_user_confirmation(contact_message)
        
        # Send notification to admin/support team
        self._send_admin_notification(contact_message)
        
        logger.info(f"Contact message #{contact_message.id} received from {contact_message.email}")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        return Response({
            "message": "Thank you for contacting us! We'll get back to you soon.",
            "data": serializer.data
        }, status=status.HTTP_201_CREATED)

    def _send_user_confirmation(self, contact_message):
        """Send confirmation email to the user who submitted the contact form"""
        
        # Generate ticket number for reference
        ticket_number = f"CONTACT-{contact_message.id:05d}"
        
        subject = 'We\'ve Received Your Message - FrameStack'
        
        # Plain text version
        plain_message = f"""
Hello {contact_message.name},

Thank you for reaching out to FrameStack! We've successfully received your message and our support team will review it shortly.

Your Reference Number: {ticket_number}

Your Message:
"{contact_message.message}"

What happens next?
• Our team typically responds within 24-48 hours
• You'll receive a detailed response to your inquiry
• For urgent matters, you can also reach us directly at support@framestack.com

We appreciate your interest in FrameStack and look forward to helping you!

Best regards,
The FrameStack Support Team

--
This is an automated confirmation. Please do not reply to this email.
"""

        # HTML version with enhanced design
        html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 0;
            background-color: #f4f5f7;
        }}
        .email-wrapper {{
            padding: 40px 20px;
            background-color: #f4f5f7;
        }}
        .email-container {{
            max-width: 600px;
            margin: 0 auto;
            background-color: #ffffff;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
            font-weight: 600;
        }}
        .header p {{
            margin: 10px 0 0 0;
            opacity: 0.95;
            font-size: 16px;
        }}
        .ticket-badge {{
            display: inline-block;
            background: rgba(255, 255, 255, 0.2);
            padding: 8px 20px;
            border-radius: 20px;
            margin-top: 15px;
            font-weight: 500;
            font-size: 14px;
        }}
        .content {{
            padding: 40px 30px;
        }}
        .greeting {{
            font-size: 18px;
            color: #333;
            margin-bottom: 20px;
        }}
        .message-box {{
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 20px;
            border-radius: 4px;
            margin: 25px 0;
        }}
        .message-box h3 {{
            margin-top: 0;
            color: #495057;
            font-size: 16px;
        }}
        .message-content {{
            color: #6c757d;
            font-style: italic;
            line-height: 1.6;
            white-space: pre-wrap;
        }}
        .timeline {{
            background: #fff;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 20px;
            margin: 25px 0;
        }}
        .timeline h3 {{
            margin-top: 0;
            color: #495057;
            font-size: 16px;
        }}
        .timeline-item {{
            display: flex;
            align-items: flex-start;
            margin: 15px 0;
        }}
        .timeline-icon {{
            width: 40px;
            height: 40px;
            background: #e8f4f8;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-right: 15px;
            flex-shrink: 0;
        }}
        .timeline-content {{
            flex: 1;
        }}
        .timeline-content h4 {{
            margin: 0 0 5px 0;
            color: #333;
            font-size: 14px;
            font-weight: 600;
        }}
        .timeline-content p {{
            margin: 0;
            color: #6c757d;
            font-size: 13px;
        }}
        .info-box {{
            background: #e8f4f8;
            border-radius: 8px;
            padding: 20px;
            margin: 25px 0;
        }}
        .info-box h3 {{
            margin-top: 0;
            color: #495057;
            font-size: 16px;
        }}
        .info-box ul {{
            margin: 10px 0;
            padding-left: 20px;
        }}
        .info-box li {{
            margin: 8px 0;
            color: #6c757d;
        }}
        .contact-methods {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            margin: 25px 0;
            text-align: center;
        }}
        .contact-methods h3 {{
            margin-top: 0;
            color: #495057;
            font-size: 16px;
        }}
        .contact-method {{
            display: inline-block;
            margin: 10px;
            padding: 10px 20px;
            background: white;
            border: 1px solid #dee2e6;
            border-radius: 6px;
            text-decoration: none;
            color: #667eea;
            font-weight: 500;
        }}
        .footer {{
            background: #f8f9fa;
            padding: 30px;
            text-align: center;
            color: #6c757d;
            font-size: 14px;
        }}
        .footer a {{
            color: #667eea;
            text-decoration: none;
        }}
        .footer a:hover {{
            text-decoration: underline;
        }}
        .social-links {{
            margin: 20px 0;
        }}
        .social-links a {{
            display: inline-block;
            margin: 0 10px;
            color: #667eea;
            text-decoration: none;
        }}
        .icon {{
            font-size: 24px;
        }}
        @media only screen and (max-width: 600px) {{
            .email-wrapper {{
                padding: 20px 10px;
            }}
            .header {{
                padding: 30px 20px;
            }}
            .content {{
                padding: 30px 20px;
            }}
        }}
    </style>
</head>
<body>
    <div class="email-wrapper">
        <div class="email-container">
            <!-- Header -->
            <div class="header">
                <div class="icon">✉️</div>
                <h1>Message Received!</h1>
                <p>We'll get back to you soon</p>
                <div class="ticket-badge">
                    Reference: {ticket_number}
                </div>
            </div>
            
            <!-- Content -->
            <div class="content">
                <div class="greeting">
                    Hello <strong>{contact_message.name}</strong> 👋
                </div>
                
                <p>
                    Thank you for reaching out to FrameStack! We've successfully received your message 
                    and our support team has been notified. We appreciate you taking the time to contact us.
                </p>
                
                <!-- User's Message -->
                <div class="message-box">
                    <h3>📝 Your Message:</h3>
                    <div class="message-content">{contact_message.message}</div>
                </div>
                
                <!-- Timeline -->
                <div class="timeline">
                    <h3>⏱️ What Happens Next?</h3>
                    
                    <div class="timeline-item">
                        <div class="timeline-icon">1️⃣</div>
                        <div class="timeline-content">
                            <h4>Message Received</h4>
                            <p>Your message has been logged in our system (Complete ✅)</p>
                        </div>
                    </div>
                    
                    <div class="timeline-item">
                        <div class="timeline-icon">2️⃣</div>
                        <div class="timeline-content">
                            <h4>Team Review</h4>
                            <p>Our support team will review your message within 24 hours</p>
                        </div>
                    </div>
                    
                    <div class="timeline-item">
                        <div class="timeline-icon">3️⃣</div>
                        <div class="timeline-content">
                            <h4>Response</h4>
                            <p>You'll receive a detailed response within 24-48 hours</p>
                        </div>
                    </div>
                </div>
                
                <!-- Response Time Info -->
                <div class="info-box">
                    <h3>📊 Our Response Times:</h3>
                    <ul>
                        <li><strong>General Inquiries:</strong> 24-48 hours</li>
                        <li><strong>Technical Support:</strong> 12-24 hours</li>
                        <li><strong>Billing Issues:</strong> Within 24 hours</li>
                        <li><strong>Partnership Requests:</strong> 3-5 business days</li>
                    </ul>
                </div>
                
                <!-- Contact Methods -->
                <div class="contact-methods">
                    <h3>Need Faster Assistance?</h3>
                    <p style="color: #6c757d; margin: 10px 0;">For urgent matters, you can reach us through:</p>
                    <a href="mailto:support@framestack.com" class="contact-method">
                        📧 support@framestack.com
                    </a>
                    <a href="{settings.FRONTEND_URL}/help" class="contact-method">
                        📚 Help Center
                    </a>
                </div>
                
                <!-- Submission Details -->
                <p style="margin-top: 30px; padding: 15px; background: #f8f9fa; border-radius: 6px; font-size: 13px; color: #6c757d;">
                    <strong>Submission Details:</strong><br>
                    📅 Date: {contact_message.created_at.strftime('%B %d, %Y at %I:%M %p')}<br>
                    📧 Email: {contact_message.email}<br>
                    🎫 Reference: {ticket_number}
                </p>
            </div>
            
            <!-- Footer -->
            <div class="footer">
                <p style="margin: 0;">
                    Thank you for choosing FrameStack!
                </p>
                <p style="margin: 10px 0;">
                    <a href="{settings.FRONTEND_URL}">Visit Website</a> | 
                    <a href="{settings.FRONTEND_URL}/help">Help Center</a> | 
                    <a href="{settings.FRONTEND_URL}/status">Service Status</a>
                </p>
                <div class="social-links">
                    <a href="#">Twitter</a> • 
                    <a href="#">LinkedIn</a> • 
                    <a href="#">Facebook</a>
                </div>
                <p style="margin: 20px 0 0 0; font-size: 12px; color: #adb5bd;">
                    © 2024 FrameStack. All rights reserved.<br>
                    This is an automated response. Please do not reply to this email.
                </p>
            </div>
        </div>
    </div>
</body>
</html>
"""

        # Send confirmation email to user via Brevo API
        send_email_async(
            subject=subject,
            message=plain_message,
            recipient_list=[contact_message.email],
            html_message=html_message
        )
        
        logger.info(f"Confirmation email sent to {contact_message.email} for contact message #{contact_message.id}")

    def _send_admin_notification(self, contact_message):
        """Send notification to admin/support team about new contact message"""
        
        # Get admin emails from settings or use default
        admin_emails = getattr(settings, 'ADMIN_EMAIL_LIST', ['admin@framestack.com', 'support@framestack.com'])
        
        ticket_number = f"CONTACT-{contact_message.id:05d}"
        
        subject = f'New Contact Form Submission - {ticket_number}'
        
        # Plain text version for admins
        plain_message = f"""
New contact form submission received:

Reference: {ticket_number}
Date: {contact_message.created_at.strftime('%B %d, %Y at %I:%M %p')}

From: {contact_message.name}
Email: {contact_message.email}

Message:
{contact_message.message}

---
Please respond within 24-48 hours.
View in admin panel: {settings.FRONTEND_URL}/admin/contact/{contact_message.id}
"""

        # HTML version for admins
        html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 20px;
            background-color: #f4f5f7;
        }}
        .container {{
            max-width: 700px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: #2c3e50;
            color: white;
            padding: 25px;
        }}
        .header h2 {{
            margin: 0;
            font-size: 24px;
        }}
        .badge {{
            display: inline-block;
            background: #e74c3c;
            color: white;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 12px;
            margin-left: 10px;
        }}
        .content {{
            padding: 30px;
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: 120px 1fr;
            gap: 15px;
            margin: 20px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 6px;
        }}
        .label {{
            font-weight: 600;
            color: #6c757d;
        }}
        .value {{
            color: #333;
        }}
        .message-section {{
            margin: 25px 0;
            padding: 20px;
            background: #fff;
            border: 1px solid #dee2e6;
            border-radius: 6px;
        }}
        .message-section h3 {{
            margin-top: 0;
            color: #495057;
        }}
        .message-content {{
            color: #333;
            white-space: pre-wrap;
            line-height: 1.8;
        }}
        .action-buttons {{
            margin: 25px 0;
            padding: 20px;
            background: #e8f4f8;
            border-radius: 6px;
            text-align: center;
        }}
        .btn {{
            display: inline-block;
            padding: 10px 25px;
            margin: 5px;
            text-decoration: none;
            border-radius: 5px;
            font-weight: 500;
        }}
        .btn-primary {{
            background: #007bff;
            color: white;
        }}
        .btn-secondary {{
            background: #6c757d;
            color: white;
        }}
        .priority {{
            padding: 15px;
            background: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 6px;
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>
                New Contact Form Submission
                <span class="badge">NEW</span>
            </h2>
        </div>
        
        <div class="content">
            <div class="priority">
                <strong>⚠️ Action Required:</strong> Please respond to this inquiry within 24-48 hours.
            </div>
            
            <div class="info-grid">
                <div class="label">Reference:</div>
                <div class="value"><strong>{ticket_number}</strong></div>
                
                <div class="label">Date:</div>
                <div class="value">{contact_message.created_at.strftime('%B %d, %Y at %I:%M %p')}</div>
                
                <div class="label">From:</div>
                <div class="value">{contact_message.name}</div>
                
                <div class="label">Email:</div>
                <div class="value">
                    <a href="mailto:{contact_message.email}" style="color: #007bff;">
                        {contact_message.email}
                    </a>
                </div>
            </div>
            
            <div class="message-section">
                <h3>Message Content:</h3>
                <div class="message-content">{contact_message.message}</div>
            </div>
            
            <div class="action-buttons">
                <a href="mailto:{contact_message.email}?subject=Re: {ticket_number}" class="btn btn-primary">
                    Reply to User
                </a>
                <a href="{settings.FRONTEND_URL}/admin/contact/{contact_message.id}" class="btn btn-secondary">
                    View in Admin Panel
                </a>
            </div>
            
            <p style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6; color: #6c757d; font-size: 13px;">
                This is an automated notification. The user has received a confirmation email with reference number {ticket_number}.
            </p>
        </div>
    </div>
</body>
</html>
"""

        # Send notification to admins via Brevo API
        send_email_async(
            subject=subject,
            message=plain_message,
            recipient_list=admin_emails,
            html_message=html_message
        )
        
        logger.info(f"Admin notification sent for contact message #{contact_message.id}")

