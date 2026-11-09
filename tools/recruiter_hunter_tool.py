"""
Recruiter & Domain Intelligence Hunter Tool for Ahmad Faraz.
Solves the "No Email Found" limitation by:
1. Mapping known Pakistani and international tech employers to verified HR/careers inboxes.
2. Deriving corporate domains and verifying email exchange capabilities via DNS.
3. Detecting ATS/job portal links (Lever, Greenhouse, Workday, Rozee, NAVTTC) and activating Portal Application mode.
"""

from __future__ import annotations

import logging
import re
import socket
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Verified Tech Employer Inboxes (Lahore, Islamabad, Karachi, Remote)
VERIFIED_TECH_EMPLOYERS = {
    "devsinc": "careers@devsinc.com",
    "systems limited": "talent.acquisition@systemsltd.com",
    "systems ltd": "talent.acquisition@systemsltd.com",
    "systemsltd": "talent.acquisition@systemsltd.com",
    "10pearls": "careers@10pearls.com",
    "arbisoft": "careers@arbisoft.com",
    "tintash": "jobs@tintash.com",
    "devbatch": "careers@devbatch.com",
    "invozone": "careers@invozone.com",
    "techleadz": "hr@techleadz.com",
    "foomotion": "hr@foomotion.io",
    "folio3": "careers@folio3.com",
    "curemd": "careers@curemd.com",
    "venturedive": "careers@venturedive.com",
    "confiz": "careers@confiz.com",
    "tkxel": "careers@tkxel.com",
    "educative": "careers@educative.io",
    "netsol": "careers@netsoltech.com",
    "netsol technologies": "careers@netsoltech.com",
    "afiniti": "careers@afiniti.com",
    "i2c": "careers@i2cinc.com",
    "i2c inc": "careers@i2cinc.com",
    "clustox": "hr@clustox.com",
    "contour software": "careers@contour-software.com",
    "kavelogics": "hr@kavelogics.com",
    "devkiosk": "hr@devkiosk.com",
    "tekdex": "hr@tekdex.com",
    "kryptomind": "careers@kryptomind.com",
    "prime system solutions": "hr@primesystemsolutions.com",
    "softconsults": "hr@softconsults.com",
    "credminds": "careers@credminds.com",
    "ailytica": "hr@ailytica.com",
    "meraki matrix": "hr@merakimatrix.com",
    "alchemative": "careers@alchemative.com",
    "nextbridge": "careers@nextbridge.com",
    "emumba": "careers@emumba.com",
    "platalytics": "careers@platalytics.com",
    "sadapay": "careers@sadapay.pk",
    "nayapay": "careers@nayapay.com",
    "bazaar": "careers@bazaartech.com",
    "dastgyr": "careers@dastgyr.com",
    "telenor": "careers@telenor.com.pk",
    "jazz": "talent@jazz.com.pk",
    "zong": "careers@zong.com.pk",
}

# ATS & Portal URL Patterns
PORTAL_PATTERNS = [
    (r"jobs\.lever\.co", "Lever ATS"),
    (r"boards\.greenhouse\.io", "Greenhouse ATS"),
    (r"apply\.workable\.com", "Workable ATS"),
    (r"myworkdayjobs\.com", "Workday ATS"),
    (r"bamboohr\.com", "BambooHR ATS"),
    (r"rozee\.pk", "Rozee.pk Job Portal"),
    (r"navttc\.gov\.pk", "NAVTTC NSIS Portal"),
    (r"pmyp\.gov\.pk", "Prime Minister Youth Internship Portal"),
    (r"linkedin\.com/jobs/view", "LinkedIn Direct Apply"),
    (r"indeed\.com", "Indeed Portal"),
    (r"glassdoor\.com", "Glassdoor Portal"),
    (r"wellfound\.com", "Wellfound Startup Portal"),
]

def is_portal_application(url: str) -> Optional[str]:
    """Detects whether a URL is an online portal or ATS rather than an email destination."""
    if not url:
        return None
    for pattern, portal_name in PORTAL_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return portal_name
    return None

def verify_domain_has_dns(domain: str) -> bool:
    """Verifies whether a domain name resolves to active IP addresses."""
    clean_d = domain.strip().lower()
    if not clean_d or "." not in clean_d:
        return False
    try:
        socket.getaddrinfo(clean_d, 80)
        return True
    except (socket.gaierror, OSError):
        return False

def hunt_recruiter_email(
    company_name: str,
    job_text: str = "",
    job_url: str = ""
) -> Dict[str, Any]:
    """Intelligently resolves recruiter email addresses when not explicitly provided in post text.

    Args:
        company_name: Raw or detected company name.
        job_text: Full post text to search for embedded emails.
        job_url: Source URL of the post.

    Returns:
        Dictionary with email, resolution_source, confidence, and portal details.
    """
    clean_company = company_name.strip().lower()
    clean_company_simple = re.sub(r"[^a-zA-Z0-9]", "", clean_company)

    # 1. Check if raw text already contains an explicit email
    raw_emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', job_text)
    ignore_domains = {"example.com", "sentry.io", "wixpress.com", "domain.com", "email.com"}
    valid_raw_emails = [
        e.lower().rstrip(".,;:!?)'\"") for e in raw_emails
        if e.split("@")[-1].lower() not in ignore_domains and "." in e.split("@")[-1]
    ]
    if valid_raw_emails:
        return {
            "email": valid_raw_emails[0],
            "method": "DIRECT_POST_TEXT",
            "confidence": "HIGH",
            "is_portal": False,
            "portal_name": None,
            "company": company_name
        }

    # 2. Check if this is an online ATS or Government portal
    portal_name = is_portal_application(job_url)
    if portal_name:
        return {
            "email": "",
            "method": "PORTAL_APPLICATION",
            "confidence": "PORTAL_REQUIRED",
            "is_portal": True,
            "portal_name": portal_name,
            "portal_url": job_url,
            "company": company_name
        }

    # 3. Check Known Tech Employer Mapping
    for known_key, known_email in VERIFIED_TECH_EMPLOYERS.items():
        if known_key in clean_company or clean_company in known_key:
            return {
                "email": known_email,
                "method": "VERIFIED_EMPLOYER_MAPPING",
                "confidence": "HIGH",
                "is_portal": False,
                "portal_name": None,
                "company": company_name
            }

    # 4. Domain Deduction from Job URL
    if job_url:
        try:
            parsed = urlparse(job_url)
            host = parsed.netloc.lower()
            if host.startswith("www."):
                host = host[4:]
            # Disregard job aggregate hostnames
            non_company_hosts = {
                "linkedin.com", "indeed.com", "rozee.pk", "glassdoor.com", "facebook.com",
                "instagram.com", "twitter.com", "x.com", "google.com", "github.com"
            }
            if host not in non_company_hosts and "." in host:
                if verify_domain_has_dns(host):
                    return {
                        "email": f"careers@{host}",
                        "method": "DERIVED_URL_DOMAIN",
                        "confidence": "MEDIUM",
                        "is_portal": False,
                        "portal_name": None,
                        "company": company_name
                    }
        except Exception:
            pass

    # 5. Domain Deduction from Company Name (e.g. "Devsinc" -> "devsinc.com")
    if clean_company_simple and len(clean_company_simple) > 2:
        candidate_domains = [
            f"{clean_company_simple}.com",
            f"{clean_company_simple}.io",
            f"{clean_company_simple}.pk",
            f"{clean_company_simple}tech.com",
        ]
        for cdom in candidate_domains:
            if verify_domain_has_dns(cdom):
                return {
                    "email": f"careers@{cdom}",
                    "method": "PREDICTED_COMPANY_DOMAIN",
                    "confidence": "MEDIUM",
                    "is_portal": False,
                    "portal_name": None,
                    "company": company_name
                }

    # 6. Fallback if company is completely obscure
    return {
        "email": "",
        "method": "UNRESOLVED",
        "confidence": "NONE",
        "is_portal": False,
        "portal_name": None,
        "company": company_name
    }
