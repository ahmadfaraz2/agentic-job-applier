"""
Job Tracking and Application History Tool for Google Antigravity SDK Agent.
Maintains state across sessions and updates the local jobs_database.json.
Compatible with Antigravity ToolContext state injection.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from config import Config

logger = logging.getLogger(__name__)

def _read_db() -> Dict[str, Any]:
    """Reads the JSON database from disk."""
    if not Config.DB_FILE.exists():
        return {"version": "1.0", "updated_at": "", "jobs": {}, "stats": {"total_evaluated": 0, "qualified": 0, "rejected": 0}}
    try:
        with open(Config.DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading database {Config.DB_FILE}: {e}")
        return {"version": "1.0", "updated_at": "", "jobs": {}, "stats": {"total_evaluated": 0, "qualified": 0, "rejected": 0}}

def _write_db(data: Dict[str, Any]) -> None:
    """Safely writes the database dictionary to disk."""
    try:
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        with open(Config.DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error writing to database {Config.DB_FILE}: {e}")

def record_job_decision(
    job_id: str,
    title: str = "",
    company: str = "",
    status: str = "",
    match_score: int = 95,
    pitch: str = "",
    job_title: str = "",
    action: str = "",
    notes: str = "",
    ctx: Optional[Any] = None,
    **kwargs: Any
) -> str:
    """Records the qualification outcome, pitch/cover letter, and tracking status for a job."""
    title = title or job_title or "Software Engineering Position"
    status = status or action or "APPLIED"
    pitch = pitch or notes or ""
    job_id = job_id.strip()
    status = status.upper().strip()

    db = _read_db()
    jobs = db.setdefault("jobs", {})
    stats = db.setdefault("stats", {"total_evaluated": 0, "qualified": 0, "rejected": 0})

    is_new = job_id not in jobs
    if is_new:
        stats["total_evaluated"] += 1
        if status in ("QUALIFIED", "APPLIED", "PENDING_USER_APPROVAL"):
            stats["qualified"] += 1
        else:
            stats["rejected"] += 1

    record = {
        "job_id": job_id,
        "title": title,
        "company": company,
        "status": status,
        "match_score": match_score,
        "pitch": pitch,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }

    jobs[job_id] = record
    _write_db(db)

    # If Antigravity ToolContext is injected, maintain in-memory state too
    if ctx and hasattr(ctx, "set_state"):
        try:
            current_state = ctx.get_state("recorded_jobs", [])
            current_state.append(job_id)
            ctx.set_state("recorded_jobs", current_state)
        except Exception:
            pass

    return f"Successfully recorded '{title}' at '{company}' as {status} (Score: {match_score}/100)."

def get_application_history(limit: int = 10, ctx: Optional[Any] = None) -> str:
    """Retrieves the recent job tracking history and aggregate stats.

    Args:
        limit: Maximum number of recent job records to return.
        ctx: Optional Antigravity ToolContext.

    Returns:
        A JSON summary of historical evaluations and statistics.
    """
    db = _read_db()
    jobs = list(db.get("jobs", {}).values())
    stats = db.get("stats", {})

    # Sort descending by evaluated_at
    jobs.sort(key=lambda x: x.get("evaluated_at", ""), reverse=True)
    recent = jobs[:limit]

    return json.dumps({
        "stats": stats,
        "recent_count": len(recent),
        "recent_jobs": recent,
    }, indent=2)
