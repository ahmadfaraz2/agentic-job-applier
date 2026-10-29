"""
Web Search Tool for Antigravity Job & Internship Automation.
Leverages DDGS (free, zero-API-key web search) and LinkedIn Guest Crawler
to find live jobs, internships, and opportunities across Lahore, Islamabad, and beyond.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Excluded domains that are tutorials/docs, not job boards
EXCLUDED_DOMAINS = [
    "python.org",
    "wikipedia.org",
    "w3schools.com",
    "geeksforgeeks.org",
    "stackoverflow.com",
    "github.com/python",
    "youtube.com",
]

def search_web_jobs(
    query: str,
    max_results: int = 8,
) -> List[Dict[str, Any]]:
    """Performs a live web search for job listings, internships, and hiring posts.

    Args:
        query: Search term (e.g. 'Python internship jobs Lahore', 'Software engineer Islamabad').
        max_results: Number of results to return.

    Returns:
        List of dictionaries with 'title', 'url', 'snippet', 'source'.
    """
    results: List[Dict[str, Any]] = []

    # Attempt with ddgs library
    try:
        from ddgs import DDGS
        with DDGS(timeout=8) as ddgs:
            raw_res = list(ddgs.text(query, max_results=max_results))
            for r in raw_res:
                url = (r.get("href") or r.get("url") or "").strip()
                title = (r.get("title") or "").strip()
                snippet = (r.get("body") or r.get("snippet") or "").strip()

                if not url or any(ex in url.lower() for ex in EXCLUDED_DOMAINS):
                    continue

                source = "Web"
                if "linkedin.com" in url:
                    source = "LinkedIn"
                elif "rozee.pk" in url:
                    source = "Rozee.pk"
                elif "indeed.com" in url:
                    source = "Indeed"
                elif "glassdoor.com" in url:
                    source = "Glassdoor"
                elif "mustakbil.com" in url:
                    source = "Mustakbil"
                elif "careers" in url or "jobs" in url:
                    source = "Company Career"

                results.append({
                    "title": title,
                    "url": url,
                    "snippet": snippet,
                    "source": source
                })
    except Exception as e:
        logger.warning(f"Web search attempt failed: {e}")

    return results

def parse_prompt_for_job_search(prompt: str) -> Dict[str, Any]:
    """Parses a natural language prompt like:
    'search for jobs in lahore, Islamabad about internships and jobs'
    and extracts targeted locations, roles, and types.
    """
    lower = prompt.lower()

    # Detect locations
    locations = []
    if "lahore" in lower:
        locations.append("Lahore")
    if "islamabad" in lower:
        locations.append("Islamabad")
    if "rawalpindi" in lower:
        locations.append("Rawalpindi")
    if "karachi" in lower:
        locations.append("Karachi")
    if "remote" in lower:
        locations.append("Remote")
    if not locations:
        locations = ["Lahore", "Islamabad"]

    # Detect types
    is_internship = any(w in lower for w in ["intern", "internship", "trainee", "fresh", "entry"])
    is_job = any(w in lower for w in ["job", "engineer", "developer", "full-time", "associate"])

    # Detect tech stack
    tech = []
    if "python" in lower:
        tech.append("Python")
    if "django" in lower:
        tech.append("Django")
    if "fastapi" in lower:
        tech.append("FastAPI")
    if "react" in lower:
        tech.append("React")
    if "ai" in lower or "agent" in lower:
        tech.append("AI")
    if not tech:
        # Default to Ahmad's core tech stack
        tech = ["Python", "Software Engineer"]

    return {
        "locations": locations,
        "is_internship": is_internship,
        "is_job": is_job,
        "tech": tech,
        "original_prompt": prompt
    }

def execute_prompt_search(prompt: str, limit_per_query: int = 5) -> List[Dict[str, Any]]:
    """Takes a natural language prompt and runs targeted web searches across locations & roles."""
    parsed = parse_prompt_for_job_search(prompt)
    locations = parsed["locations"]
    is_internship = parsed["is_internship"]
    tech_str = " ".join(parsed["tech"])

    all_results = []
    seen_urls = set()

    for loc in locations:
        queries = []
        if is_internship:
            queries.append(f"{tech_str} internship {loc} Pakistan")
        queries.append(f"{tech_str} developer jobs {loc} Pakistan")

        for q in queries:
            items = search_web_jobs(q, max_results=limit_per_query)
            for item in items:
                u = item.get("url")
                if u and u not in seen_urls:
                    seen_urls.add(u)
                    item["location"] = loc
                    all_results.append(item)

    return all_results
