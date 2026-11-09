"""
SMTP Email Dispatch Tool for Google Antigravity SDK Agent.
Supports STARTTLS (port 587) and SSL (port 465), multipart HTML/text,
CV attachments, and exact personal styling matching Ahmad Faraz's sent emails.
"""

from __future__ import annotations

import logging
import mimetypes
import os
import re
import smtplib
import threading
import time
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from pathlib import Path
from typing import List, Optional

from config import Config
from tools.excel_tracker_tool import is_already_applied, record_excel_application
from tools.pitch_customizer_tool import generate_tailored_pitch
from tools.discord_alert_tool import notify_application_sent

logger = logging.getLogger(__name__)

# Concurrency Lock for thread-safe SMTP dispatching
SMTP_LOCK = threading.Lock()

# Strict Zero-Emoji Filter for professional cold outreach
EMOJI_PATTERN = re.compile(
    r'['
    r'\U00010000-\U0010ffff'  # Supplemental Symbols, Pictographs, Emoticons
    r'\u2600-\u27ff'          # Miscellaneous Symbols & Dingbats
    r'\u2300-\u23ff'          # Miscellaneous Technical
    r'\u2b50-\u2b55'          # Stars
    r'\u200d'                 # Zero-width joiner
    r'\ufe0e\ufe0f'           # Variation selectors
    r'\u20e3'                 # Combining enclosing keycap
    r']+',
    flags=re.UNICODE
)

def strip_all_emojis(text: str) -> str:
    """Strictly strips all emojis, pictographs, dingbats, and keycaps from text."""
    if not text:
        return ""
    cleaned = EMOJI_PATTERN.sub('', text)
    return cleaned

# Dynamic CV resolution
def get_cv_path() -> Optional[Path]:
    """Finds Ahmad_Faraz_CV.pdf or falls back to any .pdf file in data/."""
    named_cv = Config.DATA_DIR / "Ahmad_Faraz_CV.pdf"
    if named_cv.exists():
        return named_cv
    pdfs = sorted(Config.DATA_DIR.glob("*.pdf"))
    if pdfs:
        return pdfs[0]
    return None

DEFAULT_CV_PATH = get_cv_path() or (Config.DATA_DIR / "your_cv.pdf")

# Standard professional signature
def get_standard_signature_text() -> str:
    name = getattr(Config, "SMTP_FROM_NAME", "") or "Job Applicant"
    phone = getattr(Config, "SENDER_PHONE", "")
    phone_part = f"\n{phone}" if phone else ""
    return f"""Regards,
{name}{phone_part}
LinkedIn: https://www.linkedin.com/in/ahmad-faraz-/
GitHub: https://github.com/ahmadfaraz2""".strip()

STANDARD_SIGNATURE_TEXT = get_standard_signature_text()

def get_standard_signature_html() -> str:
    name = getattr(Config, "SMTP_FROM_NAME", "") or "Job Applicant"
    phone = getattr(Config, "SENDER_PHONE", "")
    phone_p = f'<p style="margin: 2px 0 0 0; font-size: 14px; color: #475569;">{phone}</p>' if phone else ""
    return f"""<div style="margin-top: 24px; padding-top: 14px; border-top: 1px solid #e2e8f0; font-family: sans-serif; color: #334155;">
    <p style="margin: 0; font-weight: 600; color: #0f172a;">Regards,</p>
    <p style="margin: 2px 0 0 0; font-weight: 700; font-size: 15px; color: #0f172a;">{name}</p>
    {phone_p}
    <p style="margin: 4px 0 0 0; font-size: 13px;">
        <a href="https://www.linkedin.com/in/ahmad-faraz-/" style="color: #0284c7; text-decoration: none;">LinkedIn</a> |
        <a href="https://github.com/ahmadfaraz2" style="color: #0284c7; text-decoration: none;">GitHub</a>
    </p>
</div>""".strip()

STANDARD_SIGNATURE_HTML = get_standard_signature_html()

def get_availability_and_relocation_text(location: str = "", job_text: str = "") -> str:
    """Generates a high-conversion, friction-free availability and relocation statement.
    Adapts dynamically to the job's target city (Lahore, Islamabad/Rawalpindi, Karachi, Remote).
    Eliminates recruiter hesitation regarding relocation delays.
    """
    loc_combined = f"{location} {job_text}".lower()

    if any(k in loc_combined for k in ("lahore", "lhr")):
        return (
            "I am actively available for on-site roles in Lahore and can relocate immediately without delay, "
            "as well as remote opportunities. I've attached my CV for your review and would welcome the chance "
            "to discuss how I can contribute to your engineering team."
        )
    elif any(k in loc_combined for k in ("islamabad", "rawalpindi", "isb", "rwp")):
        return (
            "I am actively available for on-site positions in Islamabad/Rawalpindi and can join immediately upon offer, "
            "as well as remote opportunities. I've attached my CV for your review and would welcome the chance "
            "to discuss how I can contribute to your engineering team."
        )
    elif any(k in loc_combined for k in ("karachi", "khi")):
        return (
            "I am actively available for roles in Karachi and can relocate immediately without delay, "
            "as well as remote opportunities. I've attached my CV for your review and would welcome the chance "
            "to discuss how I can contribute to your engineering team."
        )
    elif any(k in loc_combined for k in ("remote", "worldwide", "anywhere", "wfh")):
        return (
            "I have a dedicated, reliable remote development setup and am fully equipped for remote engineering collaboration. "
            "I've attached my CV for your review and would be glad to discuss how I can contribute if my background is a match."
        )
    else:
        # Default for Pakistan software houses
        return (
            "I am based in Pakistan, fully prepared to relocate immediately for on-site opportunities in Lahore or Islamabad, "
            "and equally equipped for remote collaboration. I've attached my CV for your review and would welcome the opportunity "
            "to discuss how I can contribute."
        )

def send_smtp_email(
    to_email: str,
    subject: str,
    body_html: str,
    body_text: str = "",
    attachments: Optional[List[str]] = None,
) -> str:
    """Sends an email notification or application via SMTP with Ahmad Faraz's professional sender identity.

    Args:
        to_email: The recipient's email address (e.g. 'client@example.com' or 'recruiter@company.com').
        subject: The subject line of the email.
        body_html: Rich HTML formatted email body.
        body_text: Plain-text fallback for email clients that do not render HTML.
        attachments: Optional list of file paths to attach (e.g. CV / Resume PDF).

    Returns:
        A status string indicating success or the specific error encountered.
    """
    to_email = to_email.strip()
    if not to_email or "@" not in to_email:
        return f"Error: Invalid recipient email address '{to_email}'."

    # If body_text wasn't explicitly supplied, generate a basic plain-text representation
    if not body_text:
        import re
        body_text = re.sub(r"<[^>]+>", " ", body_html)
        body_text = " ".join(body_text.split())

    # Check if SMTP credentials have been configured
    if not Config.is_smtp_configured():
        msg = (
            f"[DRY-RUN SIMULATION] Simulated email from Ahmad Faraz to: {to_email}\n"
            f"Subject: {subject}\n"
            f"Body preview: {body_text[:180]}..."
        )
        logger.warning(msg)
        return f"Success (Simulated): {msg}"

    # Build MIME Email Message
    msg = EmailMessage()
    msg["Subject"] = subject
    # Real sender identity: Always Ahmad Faraz
    sender_name = "Ahmad Faraz"
    msg["From"] = formataddr((sender_name, Config.SMTP_USER))
    msg["To"] = to_email
    msg["Message-ID"] = make_msgid(domain="mail.gmail.com")

    if getattr(Config, "BCC_SELF", True) and Config.SMTP_USER:
        msg["Bcc"] = Config.SMTP_USER

    # Set pure plain text
    msg.set_content(body_text)
    
    # Only attach HTML alternative if explicitly provided
    if body_html and body_html.strip():
        msg.add_alternative(body_html, subtype="html")

    # Handle Attachments (e.g. Ahmad_Faraz_CV.pdf)
    if attachments:
        for fpath_str in attachments:
            path = Path(fpath_str)
            if not path.is_absolute():
                path = Config.DATA_DIR / path
            if path.exists() and path.is_file():
                try:
                    ctype, encoding = mimetypes.guess_type(str(path))
                    if ctype is None or encoding is not None:
                        ctype = "application/octet-stream"
                    maintype, subtype = ctype.split("/", 1)
                    with open(path, "rb") as f:
                        msg.add_attachment(
                            f.read(),
                            maintype=maintype,
                            subtype=subtype,
                            filename=path.name
                        )
                    logger.info(f"Attached file: {path.name}")
                except Exception as e:
                    logger.error(f"Failed to attach {path}: {e}")

    with SMTP_LOCK:
        max_retries = 3
        last_err = ""
        for attempt in range(1, max_retries + 1):
            try:
                if Config.SMTP_USE_SSL or Config.SMTP_PORT == 465:
                    with smtplib.SMTP_SSL(Config.SMTP_HOST, Config.SMTP_PORT, timeout=25) as server:
                        server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
                        server.send_message(msg)
                else:
                    with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT, timeout=25) as server:
                        server.ehlo()
                        if Config.SMTP_USE_TLS:
                            server.starttls()
                            server.ehlo()
                        server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
                        server.send_message(msg)

                success_msg = f"Email successfully delivered to '{to_email}' with subject '{subject}' from Ahmad Faraz."
                logger.info(success_msg)
                time.sleep(1.0)  # Gentle cooldown between sends to protect socket
                return f"Success: {success_msg}"

            except smtplib.SMTPAuthenticationError as e:
                err = f"SMTP Authentication Error ({e.smtp_code}): Please check your Gmail App Password."
                logger.error(err)
                return f"Error: {err}"
            except (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError, ConnectionResetError, TimeoutError, OSError) as e:
                last_err = f"{type(e).__name__} - {e}"
                logger.warning(f"SMTP transient connection glitch on attempt {attempt}/{max_retries}: {last_err}. Retrying in 2.0s...")
                time.sleep(2.0)
            except Exception as e:
                err = f"Failed to send email via SMTP: {type(e).__name__} - {e}"
                logger.error(err)
                return f"Error: {err}"

        err = f"Failed to send email via SMTP after {max_retries} attempts: {last_err}"
        logger.error(err)
        return f"Error: {err}"

def send_cv_application_email(
    to_email: str,
    job_title: str,
    company: str,
    custom_paragraph: str = "",
    job_description: str = "",
    source_platform: str = "Web",
    force: bool = False,
    custom_subject: str = "",
    location: str = "",
) -> str:
    """Sends a professional job application email with Ahmad Faraz's CV attached,
    matching his exact phrasing, greetings, background, and signature from previous sent emails.
    Automatically customizes skills pitch to job spec and checks Excel tracker against duplicates.

    Args:
        to_email: Recruiter or company contact email.
        job_title: The position title (e.g. 'Associate Software Engineer', 'Python AI Agent Developer').
        company: Company name (e.g. 'Rolustech', 'Lemon.io').
        custom_paragraph: Optional explicit pitch overriding the dynamic customizer.
        job_description: Job description text used by Dynamic Skills Customizer to tailor pitch.
        source_platform: Where the job was found (e.g. 'LinkedIn', 'User Paste', 'Direct').
        force: If True, bypasses deduplication check.
        custom_subject: Optional recruiter-mandated subject line override.
        location: Target job city or 'Remote' to craft high-conversion availability statement.

    Returns:
        Status string of the delivery.
    """
    to_email = to_email.strip()
    company = company.strip()
    job_title = job_title.strip()

    # Deduplication Check against Excel Tracker
    if not force and is_already_applied(recipient_email=to_email, company=company, job_title=job_title):
        msg = f"Skipped (Deduplication): Already applied to '{to_email}' for '{job_title}' at '{company}'. Duplicate outreach blocked."
        logger.info(msg)
        return f"Skipped: {msg}"

    name = getattr(Config, "SMTP_FROM_NAME", "") or "Job Applicant"
    if custom_subject and custom_subject.strip():
        subject = custom_subject.strip()
    else:
        subject = f"Application for {job_title} - {name}"

    # Enforce strict zero-emoji mandate (OUTREACH_GUIDELINES.md)
    subject = " ".join(strip_all_emojis(subject).split())
    company = " ".join(strip_all_emojis(company).split())
    job_title = " ".join(strip_all_emojis(job_title).split())

    # Dynamic tailored pitch if custom_paragraph is not supplied
    if not custom_paragraph:
        custom_paragraph = generate_tailored_pitch(
            job_title=job_title,
            company=company,
            job_description=job_description
        )

    custom_paragraph = strip_all_emojis(custom_paragraph).strip()

    availability_paragraph = get_availability_and_relocation_text(
        location=location,
        job_text=f"{job_description} {location}"
    )

    body_text = f"""Hello {company} team,

{custom_paragraph}

{availability_paragraph}

{STANDARD_SIGNATURE_TEXT}
"""

    cv_file = get_cv_path()
    attachments = []
    if cv_file and cv_file.exists():
        attachments.append(str(cv_file))

    result = send_smtp_email(
        to_email=to_email,
        subject=subject,
        body_html="",
        body_text=body_text,
        attachments=attachments
    )

    if "Success" in result:
        # Record into Excel Tracker
        record_excel_application(
            company=company,
            job_title=job_title,
            recipient_email=to_email,
            source=source_platform,
            status="APPLIED",
            cv_attached=cv_file.name if cv_file else "None",
            subject=subject,
            pitch_snippet=custom_paragraph[:200]
        )
        # Real-time Discord Notification
        notify_application_sent(
            company=company,
            job_title=job_title,
            to_email=to_email,
            source=source_platform
        )

    return result
