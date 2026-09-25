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


def send_security_alert_email(
    to_email: str,
    user_name: str,
    user_email: str,
    user_id: int | str,
    company_id: int | str | None,
    natural_language: str | None,
    attempted_sql: str | None,
    violation_type: str,
    reason: str,
    source: str = "MCP / Query System",
    timestamp: str | None = None,
) -> bool:
    """Send an immediate high-priority security alert email to SuperAdmin regarding a blocked query / injection attempt."""
    host = settings.SMTP_HOST
    if not host:
        logger.warning(
            "SMTP not configured — security alert email to %s was not sent.", to_email,
        )
        return False

    from datetime import datetime, timezone
    time_str = timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    frontend_url = (getattr(settings, "FRONTEND_URL", None) or "http://localhost:3000").rstrip("/")
    audit_link = f"{frontend_url}/dashboard/settings/audit-logs"

    nlp_display = (natural_language or "N/A").replace("<", "&lt;").replace(">", "&gt;")
    sql_display = (attempted_sql or "N/A").replace("<", "&lt;").replace(">", "&gt;")
    reason_display = reason.replace("<", "&lt;").replace(">", "&gt;")

    subject = f"[CRITICAL SECURITY ALERT] Destructive Query / Injection Blocked - {violation_type}"
    body_html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Security Alert</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; padding: 24px; color: #1e293b; background-color: #f8fafc; line-height: 1.6;">
  <div style="max-width: 680px; margin: 0 auto; background: #ffffff; border: 1px solid #fee2e2; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(239, 68, 68, 0.08);">
    
    <!-- Alert Header Banner -->
    <div style="background: linear-gradient(135deg, #b91c1c 0%, #dc2626 100%); padding: 20px 24px; color: #ffffff;">
      <div style="display: flex; align-items: center; gap: 10px;">
        <h2 style="margin: 0; font-size: 20px; font-weight: 700; letter-spacing: -0.02em;">
          &#9888; Security Guardrail Intercepted
        </h2>
      </div>
      <p style="margin: 6px 0 0 0; font-size: 14px; opacity: 0.92;">
        A prohibited destructive operation or prompt injection attempt was detected and immediately blocked.
      </p>
    </div>

    <!-- Alert Body -->
    <div style="padding: 24px;">
      
      <!-- Threat Summary Card -->
      <div style="background-color: #fef2f2; border-left: 4px solid #ef4444; border-radius: 6px; padding: 14px 16px; margin-bottom: 20px;">
        <p style="margin: 0; font-size: 14px; font-weight: 600; color: #991b1b;">
          Violation Category: <span style="color: #dc2626; text-transform: uppercase;">{violation_type}</span>
        </p>
        <p style="margin: 4px 0 0 0; font-size: 13px; color: #7f1d1d;">
          {reason_display}
        </p>
      </div>

      <!-- Execution Incident Details -->
      <h3 style="font-size: 15px; font-weight: 600; color: #334155; margin-bottom: 10px; border-bottom: 1px solid #f1f5f9; padding-bottom: 6px;">
        Incident Metadata
      </h3>
      <table style="width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 20px;">
        <tr style="border-bottom: 1px solid #f1f5f9;">
          <td style="padding: 8px 0; color: #64748b; width: 140px; font-weight: 500;">Timestamp:</td>
          <td style="padding: 8px 0; color: #0f172a; font-weight: 600;">{time_str}</td>
        </tr>
        <tr style="border-bottom: 1px solid #f1f5f9;">
          <td style="padding: 8px 0; color: #64748b; font-weight: 500;">Source / Vector:</td>
          <td style="padding: 8px 0; color: #0f172a; font-family: monospace;">{source}</td>
        </tr>
        <tr style="border-bottom: 1px solid #f1f5f9;">
          <td style="padding: 8px 0; color: #64748b; font-weight: 500;">User Full Name:</td>
          <td style="padding: 8px 0; color: #0f172a; font-weight: 600;">{user_name}</td>
        </tr>
        <tr style="border-bottom: 1px solid #f1f5f9;">
          <td style="padding: 8px 0; color: #64748b; font-weight: 500;">User Email:</td>
          <td style="padding: 8px 0; color: #2563eb; font-weight: 500;">{user_email}</td>
        </tr>
        <tr style="border-bottom: 1px solid #f1f5f9;">
          <td style="padding: 8px 0; color: #64748b; font-weight: 500;">User ID / Tenant:</td>
          <td style="padding: 8px 0; color: #0f172a;">User #{user_id} | Company #{company_id or 'System'}</td>
        </tr>
        <tr>
          <td style="padding: 8px 0; color: #64748b; font-weight: 500;">Action Taken:</td>
          <td style="padding: 8px 0; color: #15803d; font-weight: 700;">&#10004; BLOCKED (Zero database mutations permitted)</td>
        </tr>
      </table>

      <!-- NLP Prompt Input -->
      <h3 style="font-size: 14px; font-weight: 600; color: #334155; margin-bottom: 6px;">
        User Natural Language (NLP) Prompt:
      </h3>
      <div style="background-color: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 6px; padding: 12px; font-size: 13px; color: #0f172a; font-family: monospace; word-break: break-word; margin-bottom: 18px;">
        {nlp_display}
      </div>

      <!-- Attempted SQL / Payload -->
      <h3 style="font-size: 14px; font-weight: 600; color: #334155; margin-bottom: 6px;">
        Attempted SQL / Payload:
      </h3>
      <div style="background-color: #0f172a; border-radius: 6px; padding: 14px; font-size: 12px; color: #f8fafc; font-family: 'Consolas', 'Courier New', monospace; overflow-x: auto; white-space: pre-wrap; word-break: break-word; margin-bottom: 24px;">
{sql_display}
      </div>

      <!-- Action Button -->
      <div style="text-align: center; margin: 24px 0 10px 0;">
        <a href="{audit_link}"
           style="background-color: #dc2626; color: #ffffff; padding: 11px 26px;
                  border-radius: 6px; text-decoration: none; display: inline-block; font-size: 14px; font-weight: 600;">
          Inspect Incident in Audit Logs
        </a>
      </div>

      <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;" />
      <p style="margin: 0; font-size: 12px; color: #94a3b8; text-align: center;">
        This is an automated high-priority security dispatch from the Data-Taker Security &amp; MCP Guard Engine.
      </p>
    </div>
  </div>
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
            logger.info("Security alert email sent to SuperAdmin %s", to_email)
            return True
    except Exception as e:
        logger.error("Failed to send security alert email to %s: %s", to_email, e)
        return False

