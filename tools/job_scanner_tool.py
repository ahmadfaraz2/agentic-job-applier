"""
Job Scanner and Ingestion Tool for Google Antigravity SDK Agent.
Powered by HTTPX with LinkedIn public jobs crawler and pasted jobs queue (data/pasted_jobs.json).
RemoteOK has been completely removed as requested.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx

from config import Config
from tools.browser_tool import BROWSER_HEADERS, clean_html_to_markdown

logger = logging.getLogger(__name__)

PASTED_JOBS_FILE = Config.DATA_DIR / "pasted_jobs.json"

def _load_seen_job_ids() -> set:
    """Loads previously seen or processed job IDs from local database."""
    if not Config.DB_FILE.exists():
        return set()
    try:
        with open(Config.DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("jobs", {}).keys())
    except Exception as e:
        logger.warning(f"Could not load seen jobs: {e}")
        return set()

def load_pasted_jobs() -> List[Dict[str, Any]]:
    """Loads jobs that the user manually pasted into data/pasted_jobs.json."""
    if not PASTED_JOBS_FILE.exists():
        return []
    try:
        with open(PASTED_JOBS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return data.get("jobs", [])
    except Exception as e:
        logger.warning(f"Could not load pasted jobs: {e}")
    return []

def add_pasted_job(
    to_email: str,
    job_title: str,
    company: str,
    source: str = "Pasted",
    notes: str = "",
    url: str = ""
) -> str:
    """Adds a new manually found or copy-pasted job to the queue."""
    jobs = load_pasted_jobs()
    new_entry = {
        "id": f"paste_{abs(hash(to_email + job_title))}",
        "to_email": to_email.strip(),
        "job_title": job_title.strip(),
        "company": company.strip(),
        "source": source.strip(),
        "notes": notes.strip(),
        "url": url.strip(),
        "status": "PENDING"
    }
    jobs.append(new_entry)
    with open(PASTED_JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2)
    return f"Added '{job_title}' at '{company}' ({to_email}) to pasted jobs queue."

def update_pasted_job_status(identifier: str, status: str = "APPLIED") -> bool:
    """Updates the status of a job in data/pasted_jobs.json by id or recipient email."""
    from datetime import datetime, timezone
    jobs = load_pasted_jobs()
    updated = False
    for j in jobs:
        if j.get("id") == identifier or j.get("to_email", "").lower() == identifier.lower():
            j["status"] = status
            j["updated_at"] = datetime.now(timezone.utc).isoformat()
            updated = True
    if updated:
        with open(PASTED_JOBS_FILE, "w", encoding="utf-8") as f:
            json.dump(jobs, f, indent=2)
    return updated

def fetch_linkedin_public_jobs(query: str = "Python Developer", location: str = "Pakistan", limit: int = 10) -> List[Dict[str, Any]]:
    """Discovers live job postings directly from LinkedIn's public guest endpoint."""
    jobs: List[Dict[str, Any]] = []
    clean_q = query.replace(" ", "+")
    clean_loc = location.replace(" ", "+")
    url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={clean_q}&location={clean_loc}&start=0"

    try:
        with httpx.Client(headers=BROWSER_HEADERS, timeout=10.0, follow_redirects=True) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                cards = re.findall(r'<div class="base-card[^>]*>.*?</div>\s*</div>', resp.text, flags=re.DOTALL)
                for c in cards:
                    title_m = re.search(r'<h3 class="base-search-card__title">([^<]+)</h3>', c)
                    comp_m = re.search(r'<h4 class="base-search-card__subtitle">[^<]*<a[^>]*>([^<]+)</a>', c) or re.search(r'<h4 class="base-search-card__subtitle">([^<]+)</h4>', c)
                    loc_m = re.search(r'<span class="job-search-card__location">([^<]+)</span>', c)
                    link_m = re.search(r'<a class="base-card__full-link[^"]*"\s+href="([^"?]+)', c)

                    if title_m and comp_m and link_m:
                        title = title_m.group(1).strip()
                        company = comp_m.group(1).strip().replace("&amp;", "&")
                        loc = loc_m.group(1).strip() if loc_m else location
                        link = link_m.group(1).strip()
                        job_id = f"li_{abs(hash(link))}"

                        jobs.append({
                            "id": job_id,
                            "title": title,
                            "company": company,
                            "platform": "LinkedIn",
                            "rate": "Competitive Market",
                            "budget": 6000,
                            "is_remote": "remote" in f"{title} {loc}".lower(),
                            "location": loc,
                            "tags": ["Python", "Engineering", "LinkedIn"],
                            "url": link,
                            "description": f"LinkedIn position: {title} at {company} ({loc}).",
                        })
                        if len(jobs) >= limit:
                            break
    except Exception as e:
        logger.warning(f"LinkedIn public jobs query failed: {e}")

    return jobs

def scan_job_opportunities(
    query: str = "",
    min_rate: float = 0.0,
    remote_only: bool = False,
    include_linkedin: bool = True
) -> str:
    """Scans and retrieves new, unhandled job postings from:
    1. Manually pasted jobs in data/pasted_jobs.json
    2. LinkedIn live public search

    (RemoteOK is completely excluded).
    """
    query = query or Config.JOB_SEARCH_QUERY
    seen_ids = _load_seen_job_ids()

    candidates: List[Dict[str, Any]] = []

    # 1. Ingest from Ahmad's pasted jobs queue
    pasted = load_pasted_jobs()
    for p in pasted:
        jid = p.get("id") or f"paste_{abs(hash(p.get('to_email', '') + p.get('job_title', '')))}"
        if jid not in seen_ids and p.get("status") != "APPLIED":
            candidates.append({
                "id": jid,
                "title": p.get("job_title", "Software Engineer"),
                "company": p.get("company", "Company"),
                "to_email": p.get("to_email", ""),
                "platform": p.get("source", "Pasted"),
                "rate": "Competitive",
                "budget": 5000,
                "is_remote": True,
                "location": "Remote / On-site",
                "tags": ["Python", "Software Engineering", "Direct"],
                "url": p.get("url", ""),
                "description": p.get("notes", "Pasted job opening from user."),
            })

    # 2. Ingest live from LinkedIn if requested
    if include_linkedin:
        candidates.extend(fetch_linkedin_public_jobs(query="Python", location="Pakistan", limit=5))
        candidates.extend(fetch_linkedin_public_jobs(query="Python AI Agent", location="Remote", limit=5))

    # Filter out already seen and duplicates
    fresh_jobs = []
    seen_in_batch = set()

    for job in candidates:
        jid = job.get("id")
        if not jid or jid in seen_ids or jid in seen_in_batch:
            continue
        if remote_only and not job.get("is_remote", False):
            continue

        seen_in_batch.add(jid)
        fresh_jobs.append(job)

    if not fresh_jobs:
        return json.dumps({
            "status": "NO_NEW_JOBS",
            "message": "All discovered jobs have already been evaluated and processed.",
            "count": 0,
            "jobs": []
        }, indent=2)

    return json.dumps({
        "status": "SUCCESS",
        "count": len(fresh_jobs),
        "jobs": fresh_jobs
    }, indent=2)
