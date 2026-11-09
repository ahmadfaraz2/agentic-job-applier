"""
Automated Follow-Up and Multi-Channel Portal Application Tool for Ahmad Faraz.
Solves Flaw 4 by:
1. Scanning Excel tracker for applications sent >= 4 days ago with no response.
2. Generating polite, organic, zero-emoji follow-up bump emails with CV re-attached.
3. Formulating Portal Application Kits for NAVTTC, PM Youth, Rozee, and ATS portals.
"""

from __future__ import annotations

import csv
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from config import Config
from tools.excel_tracker_tool import EXCEL_FILE, CSV_FILE, update_excel_recruiter_status
from tools.email_tool import send_smtp_email, get_cv_path, STANDARD_SIGNATURE_TEXT, strip_all_emojis

logger = logging.getLogger(__name__)

def get_pending_followups(min_days: int = 4, max_days: int = 14) -> List[Dict[str, Any]]:
    """Identifies applications in tracker that were sent min_days ago and have not received a reply."""
    pending: List[Dict[str, Any]] = []
    if not CSV_FILE.exists():
        return pending

    now = datetime.now()

    try:
        with open(CSV_FILE, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                status = row.get("Status", "").strip().upper()
                if status != "APPLIED":
                    continue

                ts_str = row.get("Timestamp", "").strip()
                if not ts_str:
                    continue

                try:
                    app_date = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    continue

                days_elapsed = (now - app_date).days
                if min_days <= days_elapsed <= max_days:
                    pending.append({
                        "id": row.get("Application ID", ""),
                        "company": row.get("Company", ""),
                        "job_title": row.get("Job Title", ""),
                        "recipient_email": row.get("Recipient Email", ""),
                        "timestamp": ts_str,
                        "days_ago": days_elapsed,
                        "subject": row.get("Subject Line", "")
                    })
    except Exception as e:
        logger.warning(f"Error reading pending follow-ups: {e}")

    return pending

def generate_followup_content(record: Dict[str, Any]) -> Dict[str, str]:
    """Generates a concise, polite follow-up email adhering to zero-emoji policy."""
    company = record.get("company", "Company")
    job_title = record.get("job_title", "Software Engineer")
    orig_date = record.get("timestamp", "").split(" ")[0]
    orig_subject = record.get("subject", f"Application for {job_title} - Ahmad Faraz")

    subject = f"Following up: {orig_subject}" if not orig_subject.lower().startswith("following up") else orig_subject

    body_text = f"""Hello {company} team,

I am following up on my application sent on {orig_date} for the {job_title} role. I remain very enthusiastic about the opportunity to contribute to {company}'s software engineering team.

I have re-attached my CV for your convenience. Please let me know if any additional details would be helpful.

{STANDARD_SIGNATURE_TEXT}
"""
    return {
        "subject": strip_all_emojis(subject).strip(),
        "body_text": strip_all_emojis(body_text).strip()
    }

def send_followup_bump(record: Dict[str, Any]) -> str:
    """Dispatches the follow-up email via SMTP and updates tracker status to FOLLOWED_UP."""
    to_email = record.get("recipient_email", "").strip()
    company = record.get("company", "").strip()
    record_id = record.get("id", "")

    if not to_email:
        return "Error: No recipient email specified."

    content = generate_followup_content(record)
    cv_file = get_cv_path()
    attachments = [str(cv_file)] if cv_file and cv_file.exists() else []

    res = send_smtp_email(
        to_email=to_email,
        subject=content["subject"],
        body_html="",
        body_text=content["body_text"],
        attachments=attachments
    )

    if "Success" in res:
        update_excel_recruiter_status(
            company_or_email=to_email,
            status="FOLLOWED_UP",
            reply_snippet=f"Follow-up bump dispatched on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        return f"Success: Follow-up email sent to {company} ({to_email})."
    return res

def generate_portal_application_kit(
    company: str,
    job_title: str,
    job_description: str = "",
    portal_name: str = "Online Portal"
) -> Dict[str, str]:
    """Formulates high-impact, humanized application answers ready to copy-paste into portals."""
    about_me = (
        "I am a Software Engineering graduate with strong technical foundations in Python, modern web frameworks, "
        "and automated software testing. I have practical experience building REST APIs, managing database schemas, "
        "and developing autonomous workflows. I take pride in fast learning, writing clean code, and working collaboratively "
        "to solve production engineering problems."
    )

    why_company = (
        f"I am eager to join {company} as an adaptable, dedicated {job_title}. "
        f"I am drawn to {company}'s commitment to quality software, and I am motivated to learn production standards "
        f"from experienced mentors while contributing actively to your development sprints from day one."
    )

    cover_note = (
        f"Dear {company} Hiring Team,\n\n"
        f"I am applying for the {job_title} opening. As a Software Engineering graduate specializing in Python "
        f"and modern web systems, I have hands-on experience building backend APIs, automated test suites (Playwright/Selenium), "
        f"and scalable services. I am motivated, quick to adapt, and eager to add immediate value to your engineering sprints.\n\n"
        f"Thank you for considering my application.\n\n"
        f"{STANDARD_SIGNATURE_TEXT}"
    )

    return {
        "portal_name": portal_name,
        "company": company,
        "job_title": job_title,
        "about_me": about_me,
        "why_company": why_company,
        "cover_note": cover_note
    }
