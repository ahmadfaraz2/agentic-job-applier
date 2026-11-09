"""
Tools package for Antigravity Job Automation & Outreach Engine.
"""

from .email_tool import send_smtp_email, send_cv_application_email, get_cv_path
from .job_scanner_tool import scan_job_opportunities, fetch_linkedin_public_jobs, add_pasted_job, load_pasted_jobs, update_pasted_job_status
from .browser_tool import browse_job_page, check_cdp_available, extract_job_and_email_from_url
from .web_search_tool import search_web_jobs, execute_prompt_search, parse_prompt_for_job_search
from .excel_tracker_tool import (
    record_excel_application,
    is_already_applied,
    get_excel_stats,
    get_recent_applications,
    get_all_applied_contacts,
    update_excel_recruiter_status,
    EXCEL_FILE,
    CSV_FILE
)
from .pitch_customizer_tool import generate_tailored_pitch
from .discord_alert_tool import send_discord_notification, notify_application_sent, notify_recruiter_reply
from .inbox_listener_tool import check_inbound_recruiter_replies
from .post_parser_tool import parse_raw_job_post, strip_all_emojis
from .live_job_crawler import fetch_live_job_leads
from .recruiter_hunter_tool import hunt_recruiter_email
from .followup_tool import get_pending_followups, send_followup_bump, generate_portal_application_kit

__all__ = [
    "send_smtp_email",
    "send_cv_application_email",
    "get_cv_path",
    "scan_job_opportunities",
    "fetch_linkedin_public_jobs",
    "add_pasted_job",
    "load_pasted_jobs",
    "update_pasted_job_status",
    "browse_job_page",
    "check_cdp_available",
    "extract_job_and_email_from_url",
    "search_web_jobs",
    "execute_prompt_search",
    "parse_prompt_for_job_search",
    "record_excel_application",
    "is_already_applied",
    "get_excel_stats",
    "get_recent_applications",
    "get_all_applied_contacts",
    "update_excel_recruiter_status",
    "generate_tailored_pitch",
    "send_discord_notification",
    "notify_application_sent",
    "notify_recruiter_reply",
    "check_inbound_recruiter_replies",
    "parse_raw_job_post",
    "strip_all_emojis",
    "fetch_live_job_leads",
    "hunt_recruiter_email",
    "get_pending_followups",
    "send_followup_bump",
    "generate_portal_application_kit",
    "EXCEL_FILE",
    "CSV_FILE",
]
