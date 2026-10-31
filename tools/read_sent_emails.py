"""
Utility to read and inspect sent emails from Gmail IMAP.
Analyzes tone, style, CV submission patterns, and sender identity.
"""

from __future__ import annotations

import email
import imaplib
import sys
from email.header import decode_header
from typing import List, Dict, Any

from config import Config

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

def clean_header(val: str | None) -> str:
    if not val:
        return ""
    try:
        dh = decode_header(val)
        parts = []
        for text, enc in dh:
            if isinstance(text, bytes):
                parts.append(text.decode(enc or "utf-8", errors="replace"))
            else:
                parts.append(str(text))
        return "".join(parts)
    except Exception:
        return str(val)

def extract_body(msg: email.message.Message) -> str:
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdisp = str(part.get("Content-Disposition"))
            if ctype == "text/plain" and "attachment" not in cdisp:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    body += payload.decode(charset, errors="replace") + "\n"
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            body = payload.decode(charset, errors="replace")
    return body.strip()

def inspect_sent_mail(limit: int = 15) -> List[Dict[str, Any]]:
    mail = imaplib.IMAP4_SSL(Config.IMAP_HOST, Config.IMAP_PORT)
    mail.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
    
    # Select sent mailbox
    mail.select('"[Gmail]/Sent Mail"')
    
    status, msg_ids = mail.search(None, "ALL")
    if status != "OK" or not msg_ids[0]:
        print("No sent emails found.")
        mail.logout()
        return []

    ids = msg_ids[0].split()
    print(f"Total sent messages in mailbox: {len(ids)}")
    print(f"Inspecting the last {min(limit, len(ids))} sent messages...\n")

    results = []
    # Inspect from newest to oldest
    for msg_id in reversed(ids[-limit:]):
        res, data = mail.fetch(msg_id, "(RFC822)")
        if res != "OK":
            continue

        raw_email = data[0][1]
        msg = email.message_from_bytes(raw_email)

        subject = clean_header(msg.get("Subject"))
        sender = clean_header(msg.get("From"))
        to = clean_header(msg.get("To"))
        date = msg.get("Date")

        # Skip the test emails we generated earlier
        if "Antigravity" in subject or "Antigravity" in sender:
            continue

        body = extract_body(msg)

        # Detect attachments
        attachments = []
        if msg.is_multipart():
            for part in msg.walk():
                cdisp = str(part.get("Content-Disposition"))
                filename = part.get_filename()
                if filename or "attachment" in cdisp:
                    attachments.append(clean_header(filename or "Unnamed attachment"))

        item = {
            "id": msg_id.decode(),
            "subject": subject,
            "from": sender,
            "to": to,
            "date": date,
            "attachments": attachments,
            "body": body,
        }
        results.append(item)

    mail.logout()
    return results

if __name__ == "__main__":
    emails = inspect_sent_mail(limit=25)
    print("=" * 70)
    for idx, e in enumerate(emails, 1):
        print(f"--- EMAIL #{idx} ---")
        print(f"From:        {e['from']}")
        print(f"To:          {e['to']}")
        print(f"Date:        {e['date']}")
        print(f"Subject:     {e['subject']}")
        print(f"Attachments: {e['attachments']}")
        print(f"Body Preview:\n{e['body'][:800]}")
        print("=" * 70)
