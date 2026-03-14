

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
import threading
from typing import Optional

load_dotenv()


class EmailService:
    def __init__(self):
        self.sender_email = os.getenv("SENDER_EMAIL", "")
        self.sender_password = os.getenv("SENDER_PASSWORD", "")
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))

        if not self.sender_email or not self.sender_password:
            print("⚠️ Warning: Email credentials not configured. Email features will not work.")

    def _send_email_sync(self, to_email: str, subject: str, body: str):
        """Internal method to send email synchronously"""
        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.sender_email
            message["To"] = to_email
            html_part = MIMEText(body, "html")
            message.attach(html_part)
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(message)
            print(f"✅ Email sent to {to_email}: {subject}")
            return True
        except Exception as e:
            print(f"❌ Failed to send email to {to_email}: {e}")
            return False

    def _send_email_async(self, to_email: str, subject: str, body: str):
        """Send email in background thread (non-blocking)"""
        thread = threading.Thread(
            target=self._send_email_sync,
            args=(to_email, subject, body),
            daemon=True
        )
        thread.start()
        print(f"📧 Email queued for {to_email}: {subject}")

    # ================================================================
    # PASSWORD RESET OTP  ← NEW METHOD
    # ================================================================

    def send_reset_otp_email(self, email: str, otp: str, name: str = "User"):
        """Send password reset OTP email (ASYNC - non-blocking)"""
        subject = "Password Reset Code - AI Stress Analyzer"
        body = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family:Arial,sans-serif;background:#f0f4ff;margin:0;padding:20px;">
          <div style="max-width:500px;margin:0 auto;background:white;border-radius:16px;
                      overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
            <div style="background:linear-gradient(135deg,#2563eb,#7c3aed);
                        padding:30px;text-align:center;">
              <h1 style="color:white;margin:0;font-size:22px;">🧠 AI Stress Analyzer</h1>
            </div>
            <div style="padding:36px;">
              <h2 style="color:#1e293b;margin:0 0 8px;">Password Reset Request</h2>
              <p style="color:#64748b;margin:0 0 24px;">
                Hi {name}, use the code below to reset your password.
                It expires in <strong>10 minutes</strong>.
              </p>
              <div style="background:#f0f4ff;border:2px dashed #2563eb;border-radius:12px;
                          padding:24px;text-align:center;margin-bottom:24px;">
                <p style="margin:0 0 8px;color:#64748b;font-size:12px;
                           text-transform:uppercase;letter-spacing:1px;">Reset Code</p>
                <span style="font-size:38px;font-weight:800;letter-spacing:10px;
                             color:#2563eb;font-family:monospace;">{otp}</span>
              </div>
              <p style="color:#94a3b8;font-size:13px;margin:0;">
                If you didn't request this, ignore this email.
                Your password won't be changed.
              </p>
            </div>
            <div style="background:#f8fafc;padding:16px;text-align:center;
                        border-top:1px solid #e2e8f0;">
              <p style="margin:0;color:#94a3b8;font-size:12px;">
                © 2025 AI Stress Analyzer · Automated email, do not reply.
              </p>
            </div>
          </div>
        </body>
        </html>
        """
        self._send_email_async(email, subject, body)

    # ================================================================
    # OTP VERIFICATION (Registration)
    # ================================================================

    def send_otp_email(self, email: str, otp: str, user_type: str = "user"):
        """Send OTP verification email (ASYNC - non-blocking)"""
        subject = "Verify Your Email - AI Stress Analyzer"
        body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                          color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .otp-box {{ background: white; padding: 20px; text-align: center;
                           border: 2px dashed #667eea; border-radius: 10px; margin: 20px 0; }}
                .otp-code {{ font-size: 32px; font-weight: bold; color: #667eea;
                            letter-spacing: 5px; font-family: monospace; }}
                .warning {{ color: #e74c3c; font-size: 14px; margin-top: 10px; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🧠 AI Stress Analyzer</h1>
                    <p>Email Verification</p>
                </div>
                <div class="content">
                    <h2>Hello!</h2>
                    <p>Thank you for registering as a {user_type}. Please verify your email address to complete your registration.</p>
                    <div class="otp-box">
                        <p style="margin: 0; color: #666;">Your verification code is:</p>
                        <div class="otp-code">{otp}</div>
                        <p class="warning">⏰ This code expires in 10 minutes</p>
                    </div>
                    <p><strong>Security Note:</strong> Never share this code with anyone. Our team will never ask for your verification code.</p>
                    <p>If you didn't request this code, please ignore this email.</p>
                </div>
                <div class="footer">
                    <p>© 2025 AI Stress Analyzer. All rights reserved.</p>
                    <p>This is an automated email. Please do not reply.</p>
                </div>
            </div>
        </body>
        </html>
        """
        self._send_email_async(email, subject, body)

    # ================================================================
    # WELCOME
    # ================================================================

    def send_welcome_email(self, email: str, name: str, user_type: str = "user"):
        """Send welcome email after verification (ASYNC - non-blocking)"""
        subject = "Welcome to AI Stress Analyzer! 🎉"
        role_text = "valued user" if user_type == "user" else "healthcare professional"
        body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                          color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .feature {{ background: white; padding: 15px; margin: 10px 0; border-left: 4px solid #667eea; }}
                .cta {{ text-align: center; margin: 30px 0; }}
                .button {{ display: inline-block; padding: 15px 30px; background: #667eea;
                          color: white; text-decoration: none; border-radius: 5px; font-weight: bold; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🧠 Welcome to AI Stress Analyzer!</h1>
                </div>
                <div class="content">
                    <h2>Hi {name}! 👋</h2>
                    <p>Your email has been successfully verified. Welcome to our mental health community as a {role_text}!</p>
                    <h3>What's Next?</h3>
                    <div class="feature">
                        <strong>📝 Take Your First Assessment</strong>
                        <p>Complete our 18-question CBT-based stress assessment to get personalized insights.</p>
                    </div>
                    <div class="feature">
                        <strong>💡 Get Recommendations</strong>
                        <p>Receive AI-powered, personalized recommendations based on your stress level.</p>
                    </div>
                    <div class="feature">
                        <strong>📅 Book Appointments</strong>
                        <p>Connect with verified mental health professionals for support.</p>
                    </div>
                    <div class="feature">
                        <strong>📋 Manage Medical Records</strong>
                        <p>Upload and organize your medical documents securely in one place.</p>
                    </div>
                    <div class="cta">
                        <p>Ready to begin your mental health journey?</p>
                        <a href="http://localhost:3000/login" class="button">Go to Dashboard →</a>
                    </div>
                </div>
                <div class="footer">
                    <p>© 2025 AI Stress Analyzer. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        self._send_email_async(email, subject, body)

    # ================================================================
    # APPOINTMENTS
    # ================================================================

    def send_appointment_confirmation_email(self, user_email: str, user_name: str,
                                            doctor_name: str, appointment_time: str):
        """Send appointment confirmation email (ASYNC - non-blocking)"""
        subject = "Appointment Booked - Pending Confirmation"
        body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                          color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .info-box {{ background: white; padding: 20px; border-radius: 10px; margin: 20px 0; }}
                .status {{ background: #fff3cd; color: #856404; padding: 10px; border-radius: 5px; text-align: center; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header"><h1>📅 Appointment Booked!</h1></div>
                <div class="content">
                    <h2>Hi {user_name}!</h2>
                    <p>Your appointment request has been submitted successfully.</p>
                    <div class="info-box">
                        <h3 style="margin-top: 0;">Appointment Details:</h3>
                        <p><strong>Doctor:</strong> {doctor_name}</p>
                        <p><strong>Time Slot:</strong> {appointment_time}</p>
                    </div>
                    <div class="status">
                        <strong>⏳ Status: Pending Approval</strong>
                        <p style="margin: 5px 0 0 0; font-size: 14px;">
                            You'll receive an email once the doctor reviews your request.
                        </p>
                    </div>
                    <h3>What Happens Next?</h3>
                    <ul>
                        <li>The doctor will review your appointment request</li>
                        <li>You'll receive an email notification when they respond</li>
                        <li>If approved, prepare any questions for your session</li>
                    </ul>
                </div>
                <div class="footer"><p>© 2025 AI Stress Analyzer. All rights reserved.</p></div>
            </div>
        </body>
        </html>
        """
        self._send_email_async(user_email, subject, body)

    def send_appointment_booked_email(self, user_email: str, user_name: str,
                                      doctor_name: str, appointment_time: str,
                                      notes: Optional[str] = None):
        """Backward-compatible alias used by route handlers."""
        _ = notes
        self.send_appointment_confirmation_email(user_email, user_name, doctor_name, appointment_time)

    def send_appointment_approved_email(self, user_email: str, user_name: str,
                                        doctor_name: str, appointment_time: str):
        """Send appointment approval email (ASYNC - non-blocking)"""
        subject = "✅ Appointment Approved!"
        body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                          color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .info-box {{ background: white; padding: 20px; border-radius: 10px; margin: 20px 0;
                            border: 2px solid #10b981; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✅ Great News!</h1>
                    <p>Your Appointment is Confirmed</p>
                </div>
                <div class="content">
                    <h2>Hi {user_name}!</h2>
                    <p><strong>Your appointment has been approved!</strong></p>
                    <div class="info-box">
                        <h3 style="margin-top: 0;">Confirmed Appointment:</h3>
                        <p><strong>Doctor:</strong> {doctor_name}</p>
                        <p><strong>Time:</strong> {appointment_time}</p>
                    </div>
                    <h3>Before Your Appointment:</h3>
                    <ul>
                        <li>Prepare a list of questions or concerns</li>
                        <li>Review your stress test results</li>
                        <li>Note any symptoms or patterns you've noticed</li>
                        <li>Bring relevant medical records if needed</li>
                    </ul>
                </div>
                <div class="footer"><p>© 2025 AI Stress Analyzer. All rights reserved.</p></div>
            </div>
        </body>
        </html>
        """
        self._send_email_async(user_email, subject, body)

    def send_appointment_rejected_email(self, user_email: str, user_name: str,
                                        doctor_name: str, appointment_time: str,
                                        rejection_reason: Optional[str] = None):
        """Send appointment rejection email (ASYNC - non-blocking)"""
        subject = "Appointment Update"
        reason_text = f"<p><strong>Reason:</strong> {rejection_reason}</p>" if rejection_reason else ""
        body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                          color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .info-box {{ background: white; padding: 20px; border-radius: 10px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header"><h1>Appointment Update</h1></div>
                <div class="content">
                    <h2>Hi {user_name},</h2>
                    <p>We wanted to let you know about your appointment request with
                    <strong>{doctor_name}</strong> for <strong>{appointment_time}</strong>.</p>
                    <div class="info-box">
                        <p>Unfortunately, this time slot is no longer available.</p>
                        {reason_text}
                    </div>
                    <h3>Next Steps:</h3>
                    <ul>
                        <li>Browse other available time slots with {doctor_name}</li>
                        <li>Or explore other verified mental health professionals</li>
                    </ul>
                </div>
                <div class="footer"><p>© 2025 AI Stress Analyzer. All rights reserved.</p></div>
            </div>
        </body>
        </html>
        """
        self._send_email_async(user_email, subject, body)

    def send_appointment_completed_email(self, user_email: str, user_name: str,
                                         doctor_name: str, appointment_time: str):
        """Send appointment completion email (ASYNC - non-blocking)"""
        subject = "Thank You - Session Completed"
        body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                          color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header"><h1>Thank You! 💙</h1></div>
                <div class="content">
                    <h2>Hi {user_name},</h2>
                    <p>Thank you for completing your session with <strong>{doctor_name}</strong>
                    on <strong>{appointment_time}</strong>.</p>
                    <p>We hope it was helpful! Your mental health journey is important to us.</p>
                    <h3>Continue Your Journey:</h3>
                    <ul>
                        <li>Take regular stress assessments to track your progress</li>
                        <li>Follow your personalized recommendations</li>
                        <li>Book follow-up appointments if needed</li>
                        <li>Upload session notes to your medical records</li>
                    </ul>
                    
                    <p>Remember, taking care of your mental health is a continuous process. 
                    We're here to support you every step of the way!</p>
                </div>
                <div class="footer">
                    <p>© 2024 AI Stress Analyzer. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Send async (non-blocking)
        self._send_email_async(user_email, subject, body)


    def send_crisis_alert_email(self, user_email: str, user_name: str, crisis_reasons: list):
        """Send crisis alert email when severe stress is detected (ASYNC - non-blocking)"""
        subject = "Important: Stress Crisis Alert - AI Stress Analyzer"

        reasons_html = "".join(f"<li>{r}</li>" for r in crisis_reasons) if crisis_reasons else "<li>Consistently high stress levels detected</li>"

        body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
                          color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .alert-box {{ background: #fff5f5; border: 2px solid #e74c3c; padding: 20px;
                             border-radius: 10px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Crisis Alert</h1>
                    <p>Your well-being matters to us</p>
                </div>
                <div class="content">
                    <h2>Hi {user_name},</h2>
                    <p>Our system has detected patterns that suggest you may be experiencing significant stress.</p>

                    <div class="alert-box">
                        <strong>What we noticed:</strong>
                        <ul>{reasons_html}</ul>
                    </div>

                    <h3>Recommended Actions:</h3>
                    <ul>
                        <li>Speak with a mental health professional as soon as possible</li>
                        <li>Use our appointment booking to connect with a verified doctor</li>
                        <li>If you are in immediate danger, contact emergency services</li>
                        <li>Reach out to a trusted friend or family member</li>
                    </ul>

                    <p><strong>Helpline Numbers:</strong></p>
                    

                    <p>You are not alone. Please take care of yourself.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2026 AI Stress Analyzer. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        self._send_email_async(user_email, subject, body)


# Singleton instance
email_service = EmailService()