"""
High-Speed Smart Post Parser for Ahmad Faraz.
Takes completely raw, unformatted text from any LinkedIn post, hiring announcement,
email, or message dump, and automatically extracts:
- Company Name (with smart alias & domain resolution, e.g. systemsltd.com -> Systems Limited)
- Job Title / Role (e.g. Associate Python Engineer, SQA Intern)
- Recruiter / Application Email (e.g. talent@systemsltd.com)
- Location & Key Requirements
- Generates tailored pitch in Ahmad's authentic voice.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from tools.pitch_customizer_tool import generate_tailored_pitch

logger = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(
    r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+',
    re.IGNORECASE
)

# Known tech companies & normalization mapping
KNOWN_COMPANIES = {
    "systems limited": "Systems Limited",
    "systems ltd": "Systems Limited",
    "systemsltd": "Systems Limited",
    "rolustech": "Rolustech",
    "arbisoft": "Arbisoft",
    "10pearls": "10Pearls",
    "tenpearls": "10Pearls",
    "devsinc": "Devsinc",
    "afiniti": "Afiniti",
    "clustox": "Clustox",
    "contour software": "Contour Software",
    "contour": "Contour Software",
    "kryptomind": "KryptoMind LLC",
    "prime system solutions": "Prime System Solutions",
    "prime systems": "Prime System Solutions",
    "netsol": "NetSol Technologies",
    "netsol technologies": "NetSol Technologies",
    "curemd": "CureMD",
    "venturedive": "VentureDive",
    "tkxel": "Tkxel",
    "i2c": "i2c Inc",
    "confiz": "Confiz",
    "educative": "Educative",
    "tintash": "Tintash",
    "motive": "Motive",
    "folio3": "Folio3",
    "emumba": "Emumba",
    "invozone": "InvoZone",
    "intech": "INTECH Process Automation",
    "platalytics": "Platalytics",
    "alchemative": "Alchemative",
    "nextbridge": "Nextbridge",
    "careem": "Careem",
    "bazaar": "Bazaar Technologies",
    "dastgyr": "Dastgyr",
    "sadapay": "SadaPay",
    "nayapay": "NayaPay",
    "sastaticket": "Sastaticket.pk",
    "telenor": "Telenor",
    "jazz": "Jazz",
    "zong": "Zong CMPak",
}

# Domain to company normalization
DOMAIN_TO_COMPANY = {
    "systemsltd.com": "Systems Limited",
    "rolustech.com": "Rolustech",
    "arbisoft.com": "Arbisoft",
    "10pearls.com": "10Pearls",
    "devsinc.com": "Devsinc",
    "afiniti.com": "Afiniti",
    "clustox.com": "Clustox",
    "contour-software.com": "Contour Software",
    "kryptomind.com": "KryptoMind LLC",
    "primesystemsolutions.com": "Prime System Solutions",
    "netsoltech.com": "NetSol Technologies",
    "curemd.com": "CureMD",
    "venturedive.com": "VentureDive",
    "tkxel.com": "Tkxel",
    "i2cinc.com": "i2c Inc",
    "confiz.com": "Confiz",
    "educative.io": "Educative",
    "tintash.com": "Tintash",
    "motive.com": "Motive",
    "folio3.com": "Folio3",
    "emumba.com": "Emumba",
    "invozone.com": "InvoZone",
    "nextbridge.com": "Nextbridge",
}

# Software roles sorted by specificity (longer/more specific first)
COMMON_ROLES = [
    "associate python engineer", "associate python developer", "junior python developer",
    "associate software engineer", "junior software engineer", "software engineering intern",
    "software engineer intern", "python developer intern", "python intern",
    "associate backend engineer", "junior backend engineer", "backend developer intern",
    "associate full stack engineer", "junior full stack engineer", "full stack developer intern",
    "associate frontend engineer", "junior frontend engineer", "frontend developer intern",
    "associate sqa engineer", "junior sqa engineer", "software qa intern", "sqa intern",
    "qa engineer", "qa automation engineer", "sqa engineer", "qa intern",
    "ai engineer intern", "ai agent developer", "generative ai engineer", "machine learning intern",
    "trainee software engineer", "trainee python engineer", "trainee engineer", "trainee developer",
    "python engineer", "python developer", "django developer", "fastapi developer",
    "full stack engineer", "full stack developer", "fullstack developer",
    "backend engineer", "backend developer", "frontend engineer", "frontend developer",
    "react developer", "software engineer",
]

IGNORE_DOMAINS = {"example.com", "sentry.io", "wixpress.com", "domain.com", "email.com"}

def _extract_emails(text: str) -> List[str]:
    """Finds all valid email addresses from text."""
    found = EMAIL_REGEX.findall(text)
    clean = []
    for e in found:
        e_clean = e.strip().lower().rstrip(".,;:!?)'\"")
        domain = e_clean.split("@")[-1] if "@" in e_clean else ""
        if domain not in IGNORE_DOMAINS and "." in domain and not e_clean.endswith((".png", ".jpg", ".webp")):
            clean.append(e_clean)
    return list(dict.fromkeys(clean))

def _infer_company(text: str, email_addr: str = "") -> str:
    """Intelligently detects company name from text or email domain."""
    text_lower = text.lower()

    # Pattern 1: Explicit labels like "Company: X" or "Organization: X"
    comp_label = re.search(r'(?:Company|Organization|Employer|At company)\s*[:\-]\s*([^\n\r,]+)', text, flags=re.IGNORECASE)
    if comp_label:
        val = comp_label.group(1).strip()
        if len(val) >= 2 and len(val) < 40:
            clean_val = val.lower().strip()
            return KNOWN_COMPANIES.get(clean_val, val)

    # Pattern 2: Check known companies in text
    for comp_key, official_name in KNOWN_COMPANIES.items():
        # Match as whole word
        if re.search(r'\b' + re.escape(comp_key) + r'\b', text_lower):
            return official_name

    # Pattern 3: Domain mapping
    if email_addr and "@" in email_addr:
        domain = email_addr.split("@")[-1].lower()
        if domain in DOMAIN_TO_COMPANY:
            return DOMAIN_TO_COMPANY[domain]

    # Pattern 4: "[Company] is looking for" / "[Company] is hiring" / "[Company] is seeking"
    comp_verb = re.search(r'([A-Z][A-Za-z0-9&.\s]{1,35}?)\s+(?:is looking for|is hiring|is seeking|announces|has openings)', text)
    if comp_verb:
        candidate = comp_verb.group(1).strip().rstrip("!.,")
        # Ensure it's not a common phrase like "We", "Our team", "The company"
        if candidate.lower() not in {"we", "our team", "the company", "team"}:
            return candidate

    # Pattern 5: "hiring at X", "joining X", "careers at X", "team at X"
    hiring_at = re.search(r'(?:hiring at|join|team at|careers at|opening at|opportunity at)\s+([A-Z][A-Za-z0-9&.\s]{2,30}(?:Limited|Technologies|Solutions|Software|Pvt|LLC|Inc|Labs|Studio)?)', text, flags=re.IGNORECASE)
    if hiring_at:
        return hiring_at.group(1).strip().rstrip("!.,")

    # Pattern 6: Format email domain if not generic provider
    if email_addr and "@" in email_addr:
        domain = email_addr.split("@")[-1].lower()
        generic = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com"}
        if domain not in generic:
            parts = domain.split(".")[0]
            return parts.capitalize()

    return "Company"

def _clean_role_title(title: str) -> str:
    """Cleans and capitalizes role title, stripping stray bullets/arrows and preserving acronyms."""
    # Strip leading bullet points, emojis, arrows, or dashes
    title = re.sub(r'^[→•\-\*\:\>\s]+', '', title.strip())
    words = title.strip().split()
    formatted = []
    acronyms = {"qa": "QA", "sqa": "SQA", "ai": "AI", "api": "API", "ml": "ML"}
    for w in words:
        w_lower = w.lower()
        if w_lower in acronyms:
            formatted.append(acronyms[w_lower])
        else:
            formatted.append(w.capitalize())
    return " ".join(formatted)

def _infer_role(text: str) -> str:
    """Extracts job title from text."""
    # Pattern 1: Explicit labels like "Role: X" or "Position: X" or "Job Title: X"
    role_label = re.search(r'(?:Role|Position|Job Title|Title|Opening|Hiring for)\s*[:\-]\s*([^\n\r,]+)', text, flags=re.IGNORECASE)
    if role_label:
        val = role_label.group(1).strip()
        if len(val) >= 3 and len(val) < 50:
            return _clean_role_title(val)

    # Pattern 2: Contextual verb phrase "looking for an? <Role>" or "hiring an? <Role>"
    verb_role = re.search(r'(?:looking for|hiring for|hiring an?|seeking an?|position of|role of|opening for)\s+(?:an?\s+)?([A-Za-z\s/]{2,45}?(?:Engineer|Developer|Intern|Specialist|Consultant|Architect|Lead|Associate|Analyst|Trainee|Tester))', text, flags=re.IGNORECASE)
    if verb_role:
        candidate = verb_role.group(1).strip()
        if len(candidate) >= 3:
            return _clean_role_title(candidate)

    # Pattern 3: Check standard roles sorted by length (most specific first)
    text_lower = text.lower()
    for role in COMMON_ROLES:
        if re.search(r'\b' + re.escape(role) + r'\b', text_lower):
            return _clean_role_title(role)

    return "Software Engineer"

def _infer_location(text: str) -> str:
    """Detects Pakistani or remote tech hubs from text."""
    text_lower = text.lower()
    locs = []
    if "lahore" in text_lower:
        locs.append("Lahore")
    if "islamabad" in text_lower:
        locs.append("Islamabad")
    if "rawalpindi" in text_lower:
        locs.append("Rawalpindi")
    if "karachi" in text_lower:
        locs.append("Karachi")
    if "remote" in text_lower:
        locs.append("Remote")

    if locs:
        return ", ".join(locs)
    return "Lahore / Remote"

def parse_raw_job_post(raw_text: str) -> Dict[str, Any]:
    """Instantly parses raw LinkedIn posts, emails, or job listings into structured data."""
    raw_text = raw_text.strip()
    if not raw_text:
        return {"status": "ERROR", "message": "Raw post text is empty."}

    # 1. Extract email addresses
    emails = _extract_emails(raw_text)
    primary_email = emails[0] if emails else ""

    # 2. Extract company, role, location
    company = _infer_company(raw_text, email_addr=primary_email)
    job_title = _infer_role(raw_text)
    location = _infer_location(raw_text)

    # 3. Generate tailored pitch based on extracted parameters & full post requirements
    pitch = generate_tailored_pitch(
        job_title=job_title,
        company=company,
        job_description=raw_text
    )

    return {
        "status": "SUCCESS",
        "company": company,
        "job_title": job_title,
        "recruiter_email": primary_email,
        "discovered_emails": emails,
        "location": location,
        "tailored_pitch": pitch,
        "raw_text_length": len(raw_text)
    }
