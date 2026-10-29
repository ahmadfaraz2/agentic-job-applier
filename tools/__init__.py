"""
Tools package for Antigravity Job Automation Agent.
"""

from .email_tool import send_smtp_email, send_cv_application_email
from .job_scanner_tool import scan_job_opportunities, fetch_linkedin_public_jobs, add_pasted_job, load_pasted_jobs, update_pasted_job_status
from .tracker_tool import record_job_decision, get_application_history
from .browser_tool import browse_job_page, check_cdp_available, extract_job_and_email_from_url
from .web_search_tool import search_web_jobs, execute_prompt_search, parse_prompt_for_job_search
from .excel_tracker_tool import record_excel_application, is_already_applied, get_excel_stats, EXCEL_FILE, CSV_FILE

__all__ = [
    "send_smtp_email",
    "send_cv_application_email",
    "scan_job_opportunities",
    "fetch_linkedin_public_jobs",
    "add_pasted_job",
    "load_pasted_jobs",
    "update_pasted_job_status",
    "record_job_decision",
    "get_application_history",
    "browse_job_page",
    "check_cdp_available",
    "extract_job_and_email_from_url",
    "search_web_jobs",
    "execute_prompt_search",
    "parse_prompt_for_job_search",
    "record_excel_application",
    "is_already_applied",
    "get_excel_stats",
    "EXCEL_FILE",
    "CSV_FILE",
]
