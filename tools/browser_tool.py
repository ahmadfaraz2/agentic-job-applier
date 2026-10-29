"""
Browser Agent Skill & Tool for Antigravity Job Automation.
Uses HTTPX with browser fingerprinting (User-Agent, headers) and Chrome DevTools Protocol (CDP)
to browse live job boards, extract rendered DOM content, and inspect opportunities.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional
import httpx

from config import Config

logger = logging.getLogger(__name__)

# Modern Chrome Browser Headers
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}

def clean_html_to_markdown(html_content: str, max_chars: int = 4000) -> str:
    """Strips tags, scripts, and stylesheets, converting page text to clean readable text."""
    text = re.sub(r"<(script|style|svg|noscript)[^>]*>.*?</\1>", " ", html_content, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<a\s+[^>]*href="([^"]+)"[^>]*>(.*?)</a>', r'[\2](\1)', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<h[1-3][^>]*>(.*?)</h[1-3]>', r'\n### \1\n', text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    cleaned = "\n".join(lines)
    return cleaned[:max_chars]

async def check_cdp_available(cdp_url: str = "http://127.0.0.1:9222") -> Optional[str]:
    """Checks if a local Chrome/Edge instance is running with remote debugging enabled."""
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            resp = await client.get(f"{cdp_url}/json/version")
            if resp.status_code == 200:
                data = resp.json()
                return data.get("Browser", "Chrome/CDP")
    except Exception:
        pass
    return None

async def browse_job_page(url: str, extract_summary: bool = True) -> str:
    """Navigates to a given job listing URL using browser emulation and extracts detailed requirements.

    Args:
        url: The web URL of the job posting to inspect.
        extract_summary: Whether to return sanitized, structured content instead of raw HTML.

    Returns:
        Extracted text content including job scope, responsibilities, compensation, and qualifications.
    """
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        return f"Error: Invalid URL scheme for '{url}'."

    logger.info(f"[BrowserAgent] Navigating to: {url}")

    async with httpx.AsyncClient(
        headers=BROWSER_HEADERS,
        follow_redirects=True,
        timeout=15.0
    ) as client:
        try:
            response = await client.get(url)
            if response.status_code != 200:
                return f"Error: Browser navigation failed with HTTP {response.status_code} ({response.reason_phrase})."

            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                return json.dumps(response.json(), indent=2)[:3000]

            raw_html = response.text
            if extract_summary:
                cleaned = clean_html_to_markdown(raw_html)
                return f"[Source: {url}]\n\n{cleaned}"
            return raw_html[:3000]

        except httpx.TimeoutException:
            return f"Error: Browser timed out while requesting {url}."
        except Exception as e:
            logger.error(f"Browser error on {url}: {e}")
            return f"Error: Browser failed to fetch {url}: {type(e).__name__} - {e}"

async def extract_job_and_email_from_url(url: str) -> Dict[str, Any]:
    """Inspects any arbitrary job URL, extracting job title, company name, requirements,
    and any recruiter/hiring contact email addresses found in the page text.

    Args:
        url: Any job posting URL (LinkedIn, company career page, Greenhouse, Lever, etc.).

    Returns:
        Dictionary containing extracted metadata, candidate emails, and cleaned text.
    """
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        return {"status": "ERROR", "message": f"Invalid URL: {url}"}

    async with httpx.AsyncClient(headers=BROWSER_HEADERS, follow_redirects=True, timeout=15.0) as client:
        try:
            resp = await client.get(url)
            if resp.status_code != 200:
                return {"status": "ERROR", "message": f"HTTP {resp.status_code}"}

            html = resp.text
            markdown = clean_html_to_markdown(html, max_chars=5000)

            # Search for contact emails
            # Look for mailto: links first
            mailtos = re.findall(r'mailto:([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', html, flags=re.IGNORECASE)
            
            # Look for plain email addresses in text
            plain_emails = re.findall(r'[bB]y\s+email\s+to\s+([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)|[a-zA-Z0-9_.+-]+@(?!example\.com|sentry\.io|wixpress)[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', html)

            # Flatten and filter emails
            all_emails = set()
            for e in mailtos:
                if len(e) < 50 and "." in e.split("@")[-1]:
                    all_emails.add(e.lower())
            for e in plain_emails:
                if isinstance(e, str) and "@" in e and len(e) < 50 and not e.endswith((".png", ".jpg", ".webp")):
                    all_emails.add(e.lower())

            # Attempt to extract job title
            title_m = re.search(r'<h1[^>]*>([^<]+)</h1>', html, flags=re.IGNORECASE) or re.search(r'<title>([^<|]+)', html, flags=re.IGNORECASE)
            title = title_m.group(1).strip() if title_m else "Software Engineering Position"

            # Attempt company extraction from title or URL or metadata
            company = "Company"
            comp_tag = re.search(r'topcard__org-name-link[^>]*>([^<]+)</a>', html, flags=re.IGNORECASE) or re.search(r'data-tracking-control-name="public_jobs_topcard-org-name"[^>]*>([^<]+)</a>', html, flags=re.IGNORECASE)
            if comp_tag:
                company = comp_tag.group(1).strip()
            elif " at " in title:
                parts = title.split(" at ")
                title = parts[0].strip()
                company = re.split(r'[–—\-|]', parts[1])[0].strip()
            elif " | " in title:
                parts = title.split(" | ")
                title = parts[0].strip()
                company = re.split(r'[–—\-|]', parts[1])[0].strip()

            return {
                "status": "SUCCESS",
                "url": url,
                "title": title,
                "company": company,
                "emails": list(all_emails),
                "summary": markdown[:1500],
            }

        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
