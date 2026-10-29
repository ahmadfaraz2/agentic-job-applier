"""
Inbound Reply & Interview Detection Engine (IMAP Listener) for Ahmad Faraz.
Connects to Gmail IMAP, monitors for recruiter responses, classifies replies
(Interview Invites, Assessments, Inquiries, Rejections), updates Excel tracking,
and triggers real-time Discord priority notifications.
"""

from __future__ import annotations

import email
from email.header import decode_header
import imaplib
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from config import Config
from tools.excel_tracker_tool import update_excel_recruiter_status, get_excel_stats
from tools.discord_alert_tool import notify_recruiter_reply

logger = logging.getLogger(__name__)

# Keywords for AI Classification
INTERVIEW_KEYWORDS = [
    "interview", "schedule", "call", "meeting", "meet", "discussion",
    "zoom", "google meet", "teams", "available for", "time slot",
    "congratulations", "shortlist", "shortlisted", "next round", "phone screen"
]

ASSESSMENT_KEYWORDS = [
    "assessment", "test", "coding challenge", "hackerrank", "codility",
    "technical task", "assignment", "take-home", "take home", "quiz"
]

REJECTION_KEYWORDS = [
    "unfortunately", "other candidates", "not moving forward", "regret to inform",
    "pursue other", "decided not to", "at this time", "kept on file"
]

INQUIRY_KEYWORDS = [
    "salary", "expectation", "notice period", "when can you join",
    "portfolio", "github", "current location", "relocation"
]

def _decode_mime_words(raw_header: Optional[str]) -> str:
    """Decodes MIME encoded header strings (e.g. utf-8, base64)."""
    if not raw_header:
        return ""
    decoded_fragments = []
    for frag, enc in decode_header(raw_header):
        if isinstance(frag, bytes):
            try:
                decoded_fragments.append(frag.decode(enc or "utf-8", errors="replace"))
            except Exception:
                decoded_fragments.append(frag.decode("latin1", errors="replace"))
        else:
            decoded_fragments.append(str(frag))
    return " ".join(decoded_fragments).strip()

def _extract_body_text(msg: email.message.Message, max_chars: int = 1500) -> str:
    """Extracts clean plain-text body content from an email message."""
    body_parts = []
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdisp = str(part.get("Content-Disposition", ""))
            if ctype == "text/plain" and "attachment" not in cdisp:
                payload = part.get_payload(decode=True)
                if payload:
                    body_parts.append(payload.decode("utf-8", errors="replace"))
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body_parts.append(payload.decode("utf-8", errors="replace"))

    full_body = "\n".join(body_parts).strip()
    return full_body[:max_chars]

def classify_recruiter_email(subject: str, body: str) -> str:
    """Classifies an incoming recruiter message into actionable categories."""
    combined = f"{subject} {body}".lower()

    # Check for Interview Invite first (highest priority)
    if any(k in combined for k in INTERVIEW_KEYWORDS) and not any(r in combined for r in REJECTION_KEYWORDS):
        return "INTERVIEW_INVITE"

    # Check for Technical Assessment / Coding Test
    if any(k in combined for k in ASSESSMENT_KEYWORDS):
        return "ASSESSMENT"

    # Check for Rejection
    if any(k in combined for k in REJECTION_KEYWORDS):
        return "REJECTION"

    # Check for General Inquiries
    if any(k in combined for k in INQUIRY_KEYWORDS):
        return "INQUIRY"

    return "GENERAL_REPLY"

def check_inbound_recruiter_replies(
    limit: int = 30,
    notify_discord: bool = True
) -> List[Dict[str, Any]]:
    """Connects to Gmail IMAP, checks recent messages for recruiter replies,
    updates Excel tracker, and triggers Discord notifications.

    Returns:
        List of matched recruiter responses with company, sender, category, and subject.
    """
    if not Config.SMTP_USER or not Config.SMTP_PASSWORD:
        logger.warning("[Inbox Listener] Gmail credentials not configured.")
        return []

    stats = get_excel_stats()
    applied_companies = [c.lower() for c in stats.get("companies", [])]
    if not applied_companies:
        logger.info("[Inbox Listener] No applied companies found in Excel tracker.")
        return []

    matched_replies: List[Dict[str, Any]] = []

    try:
        mail = imaplib.IMAP4_SSL(Config.IMAP_HOST, Config.IMAP_PORT, timeout=15)
        mail.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
        mail.select("INBOX", readonly=True)

        # Search for recent messages in inbox
        status, messages = mail.search(None, "ALL")
        if status != "OK" or not messages or not messages[0]:
            mail.logout()
            return []

        msg_ids = messages[0].split()
        recent_ids = msg_ids[-limit:]  # Inspect the latest N emails

        for mid in reversed(recent_ids):
            try:
                res, data = mail.fetch(mid, "(RFC822)")
                if res != "OK" or not data or not data[0]:
                    continue

                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)

                sender = _decode_mime_words(msg.get("From"))
                subject = _decode_mime_words(msg.get("Subject"))
                date_str = _decode_mime_words(msg.get("Date"))

                sender_lower = sender.lower()
                subject_lower = subject.lower()

                # Check if sender matches any company we applied to
                matched_company = None
                for comp in applied_companies:
                    clean_c = comp.replace(" ", "").replace("-", "").replace(".", "")
                    if comp in sender_lower or clean_c in sender_lower or comp in subject_lower:
                        matched_company = comp.title()
                        break

                if matched_company:
                    body = _extract_body_text(msg)
                    classification = classify_recruiter_email(subject, body)
                    clean_snippet = " ".join(body.split())[:200]

                    reply_data = {
                        "company": matched_company,
                        "sender": sender,
                        "subject": subject,
                        "date": date_str,
                        "classification": classification,
                        "snippet": clean_snippet
                    }
                    matched_replies.append(reply_data)

                    # Update Excel Tracker status
                    update_excel_recruiter_status(
                        company_or_email=matched_company,
                        status=classification,
                        reply_snippet=f"{subject} - {clean_snippet}"
                    )

                    # Real-time Discord Alert
                    if notify_discord:
                        notify_recruiter_reply(
                            company=matched_company,
                            sender_email=sender,
                            classification=classification,
                            subject=subject,
                            snippet=clean_snippet
                        )

            except Exception as e:
                logger.debug(f"Error parsing message ID {mid}: {e}")

        mail.logout()

    except Exception as e:
        logger.error(f"[Inbox Listener] IMAP check error: {e}")

    return matched_replies
