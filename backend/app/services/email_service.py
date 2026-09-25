import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import settings

logger = logging.getLogger(__name__)


def send_reset_email(to_email: str, token: str) -> None:
    host = settings.SMTP_HOST
    if not host:
        logger.warning(
            "SMTP not configured — password reset email for %s was not sent. "
            "The reset token is stored in the database.", to_email,
        )
        return

    frontend_url = (getattr(settings, "FRONTEND_URL", None) or "http://localhost:3000").rstrip("/")
    reset_link = f"{frontend_url}/reset-password?token={token}"

    subject = "Password Reset — Agentic Analytics"
    body_html = f"""<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; padding: 24px; color: #333; line-height: 1.6;">
  <h2 style="color: #4f46e5; margin-bottom: 16px;">Password Reset Request</h2>
  <p>We received a request to reset your password for <strong>Agentic Analytics</strong>.</p>
  <p>Click the button below to set a new password. This link expires in 30 minutes.</p>
  <p style="text-align: center; margin: 28px 0;">
    <a href="{reset_link}"
       style="background-color: #6366f1; color: #fff; padding: 12px 32px;
              border-radius: 6px; text-decoration: none; display: inline-block; font-weight: bold;">
      Reset Password
    </a>
  </p>
  <p style="font-size: 14px; color: #555; margin-bottom: 6px;">If the button above does not open directly, copy and paste this link in your browser:</p>
  <p style="font-size: 13px; word-break: break-all; background-color: #f3f4f6; padding: 10px 14px; border-radius: 6px; margin-bottom: 16px;">
    <a href="{reset_link}" style="color: #4f46e5;">{reset_link}</a>
  </p>
  <p style="font-size: 14px; color: #555; margin-bottom: 6px;">Or enter this Reset Token / Code on the reset password screen:</p>
  <p style="font-family: monospace; font-size: 15px; font-weight: bold; background: #eef2ff; color: #4338ca; padding: 10px 14px; border-radius: 6px; display: inline-block; word-break: break-all;">
    {token}
  </p>
  <p style="margin-top: 24px; font-size: 13px; color: #6b7280;">If you didn't request this, you can safely ignore this email.</p>
  <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 20px 0;" />
  <p style="font-size: 12px; color: #9ca3af;">Agentic Analytics &mdash; {frontend_url}</p>
</body>
</html>"""

    msg = MIMEMultipart("alternative")
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body_html, "html"))

    try:
        with smtplib.SMTP(host, settings.SMTP_PORT, timeout=10) as server:
            if settings.SMTP_PORT == 587:
                server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
            logger.info("Reset email sent to %s", to_email)
    except Exception as e:
        logger.error("Failed to send reset email to %s: %s", to_email, e)
        logger.warning(
            "Password reset email for %s could not be sent. "
            "The reset token is stored in the database.", to_email,
        )
