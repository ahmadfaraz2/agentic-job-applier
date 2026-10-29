"""
SMTP Configuration & Direct Connection Test Utility.
Run this script to verify your SMTP server, port, credentials, and TLS/SSL settings.
"""

from __future__ import annotations

import sys
import io

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
from config import Config
from tools.email_tool import send_smtp_email

def run_smtp_test() -> bool:
    print("=" * 60)
    print("  Antigravity SMTP Configuration Test")
    print("=" * 60)
    print(f"SMTP Host:      {Config.SMTP_HOST}")
    print(f"SMTP Port:      {Config.SMTP_PORT}")
    print(f"TLS Enabled:    {Config.SMTP_USE_TLS}")
    print(f"SSL Enabled:    {Config.SMTP_USE_SSL}")
    print(f"Sender Email:   {Config.SMTP_FROM_EMAIL}")
    print(f"Sender Name:    {Config.SMTP_FROM_NAME}")
    print(f"Recipient:      {Config.ALERT_RECIPIENT_EMAIL or '(Not configured in .env)'}")
    print("-" * 60)

    if not Config.is_smtp_configured():
        print("\n[!] NOTICE: SMTP credentials are not yet fully configured in your .env file.")
        print("    The tool will run in [DRY-RUN SIMULATION] mode.")
        print("    To send real emails, edit your .env file and set:")
        print("      - SMTP_HOST, SMTP_PORT")
        print("      - SMTP_USER, SMTP_PASSWORD")
        print("      - ALERT_RECIPIENT_EMAIL\n")

    recipient = Config.ALERT_RECIPIENT_EMAIL or "test@example.com"
    subject = "🧪 Test Message: Antigravity Job Automation & SMTP Setup"
    body_html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #ffffff;">
        <h2 style="color: #1e293b; margin-top: 0;">🚀 Antigravity SMTP Test Successful</h2>
        <p style="color: #475569; font-size: 15px; line-height: 1.6;">
            Your SMTP email delivery configuration for the <strong>Google Antigravity SDK Job Automation Engine</strong> is working properly.
        </p>
        <div style="background-color: #f8fafc; border-left: 4px solid #3b82f6; padding: 14px; margin: 18px 0; border-radius: 4px;">
            <p style="margin: 0; font-size: 14px; color: #334155;"><strong>Host:</strong> {Config.SMTP_HOST}:{Config.SMTP_PORT}</p>
            <p style="margin: 4px 0 0; font-size: 14px; color: #334155;"><strong>Sender:</strong> {Config.SMTP_FROM_NAME} &lt;{Config.SMTP_FROM_EMAIL}&gt;</p>
        </div>
        <p style="color: #64748b; font-size: 13px; margin-bottom: 0;">
            Next step: The autonomous agent will use this channel to deliver real-time job digests and application confirmations.
        </p>
    </div>
    """
    body_text = "Test Message: Antigravity Job Automation SMTP email is configured and working."

    print(f"Attempting delivery to: {recipient}...")
    result = send_smtp_email(
        to_email=recipient,
        subject=subject,
        body_html=body_html,
        body_text=body_text
    )
    print("\nResult:")
    print(f"  {result}")
    print("=" * 60)
    return "Success" in result

if __name__ == "__main__":
    success = run_smtp_test()
    sys.exit(0 if success else 1)
