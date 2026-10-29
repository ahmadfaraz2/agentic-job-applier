"""
Real-Time Discord Alert Tool for Ahmad Faraz Job Outreach Engine.
Sends formatted Discord embed notifications via Webhook for:
- Dispatched applications
- Recruiter replies & interview invites
- High-match job discoveries
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx

from config import Config

logger = logging.getLogger(__name__)

COLOR_SENT = 0x3B82F6       # Blue
COLOR_INTERVIEW = 0x22C55E  # Bright Green
COLOR_ASSESSMENT = 0xF59E0B # Amber
COLOR_REPLY = 0x06B6D4      # Cyan
COLOR_DISCOVERY = 0x8B5CF6  # Purple
COLOR_REJECTED = 0x64748B   # Slate Gray

def send_discord_notification(
    title: str,
    description: str,
    fields: Optional[List[Dict[str, Any]]] = None,
    color: int = COLOR_SENT,
    url: Optional[str] = None
) -> bool:
    """Dispatches a rich embed notification to the configured Discord channel.

    Args:
        title: Notification header title.
        description: Main message description.
        fields: Optional list of {'name': ..., 'value': ..., 'inline': True/False}.
        color: Hex color integer for the embed sidebar.
        url: Optional clickable link on the embed title.

    Returns:
        True if successfully posted to Discord, False otherwise.
    """
    webhook_url = Config.DISCORD_WEBHOOK_URL.strip()
    if not webhook_url:
        logger.debug("[Discord Alert] DISCORD_WEBHOOK_URL not configured. Skipping alert.")
        return False

    if not webhook_url.startswith("https://discord.com/api/webhooks/") and not webhook_url.startswith("https://discordapp.com/api/webhooks/"):
        logger.warning(f"[Discord Alert] Invalid Discord Webhook URL: {webhook_url[:30]}...")
        return False

    embed: Dict[str, Any] = {
        "title": title,
        "description": description,
        "color": color,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "footer": {
            "text": "Ahmad Faraz Job Outreach Engine • Powered by Google Antigravity",
            "icon_url": "https://cdn-icons-png.flaticon.com/512/281/281769.png"
        }
    }

    if url:
        embed["url"] = url

    if fields:
        embed["fields"] = fields

    payload = {
        "username": "Ahmad Faraz Outreach Bot",
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/9131/9131529.png",
        "embeds": [embed]
    }

    try:
        with httpx.Client(timeout=8.0) as client:
            resp = client.post(webhook_url, json=payload)
            if resp.status_code in (200, 204):
                logger.info(f"[Discord Alert] Successfully posted notification: '{title}'")
                return True
            else:
                logger.warning(f"[Discord Alert] Discord API returned {resp.status_code}: {resp.text}")
                return False
    except Exception as e:
        logger.error(f"[Discord Alert] Failed to dispatch Discord notification: {e}")
        return False

def notify_application_sent(
    company: str,
    job_title: str,
    to_email: str,
    source: str = "Direct",
    cv_file: str = "Ahmad_Faraz_CV.pdf"
) -> bool:
    """Sends a Discord notification when a job application email is dispatched."""
    title = f"🚀 Application Dispatched: {job_title}"
    desc = f"Successfully delivered application email to **{company}** with CV attached."
    fields = [
        {"name": "🏢 Company", "value": company, "inline": True},
        {"name": "💼 Position", "value": job_title, "inline": True},
        {"name": "📬 Recipient", "value": f"`{to_email}`", "inline": True},
        {"name": "📄 CV Attached", "value": cv_file, "inline": True},
        {"name": "🌐 Origin", "value": source, "inline": True},
        {"name": "📊 Tracker", "value": "`applied_jobs_tracker.xlsx`", "inline": True},
    ]
    return send_discord_notification(title, desc, fields=fields, color=COLOR_SENT)

def notify_recruiter_reply(
    company: str,
    sender_email: str,
    classification: str,
    subject: str,
    snippet: str
) -> bool:
    """Sends an immediate priority alert when a recruiter replies."""
    color_map = {
        "INTERVIEW_INVITE": COLOR_INTERVIEW,
        "ASSESSMENT": COLOR_ASSESSMENT,
        "INQUIRY": COLOR_REPLY,
        "REJECTION": COLOR_REJECTED
    }
    color = color_map.get(classification, COLOR_REPLY)

    badge = "💬 RECRUITER REPLY"
    if classification == "INTERVIEW_INVITE":
        badge = "🟢 INTERVIEW INVITE DETECTED"
    elif classification == "ASSESSMENT":
        badge = "🟡 TECHNICAL TEST / ASSESSMENT"
    elif classification == "REJECTION":
        badge = "🔴 STATUS UPDATE (REJECTION)"

    title = f"{badge}: {company}"
    desc = f"New response received from **{company}** (`{sender_email}`)!"
    fields = [
        {"name": "🏢 Company", "value": company, "inline": True},
        {"name": "📋 Category", "value": f"**{classification.replace('_', ' ')}**", "inline": True},
        {"name": "✉️ Subject", "value": subject[:80], "inline": False},
        {"name": "📝 Message Snippet", "value": f"```{snippet[:300]}```", "inline": False},
    ]
    return send_discord_notification(title, desc, fields=fields, color=color)
