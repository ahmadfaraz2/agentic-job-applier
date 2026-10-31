"""
High-Speed Smart Post Parser for Ahmad Faraz.
Takes completely raw, unformatted text from any LinkedIn post, hiring announcement,
email, or message dump, and automatically extracts:
- Company Name (with smart alias & domain resolution, e.g. systemsltd.com -> Systems Limited)
- Job Title / Role (e.g. SE Intern, Associate Python Engineer)
- Recruiter / Application Email (e.g. hr@devkiosk.com, talent@systemsltd.com)
- Recruiter-Mandated Subject Line (e.g. 'SE Intern – Ahmad Faraz')
- Location & Key Requirements
- Generates dynamically tailored, humanized pitch in Ahmad's authentic voice.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from tools.pitch_customizer_tool import generate_tailored_pitch

logger = logging.getLogger(__name__)

CANDIDATE_NAME = "Ahmad Faraz"

EMAIL_REGEX = re.compile(
    r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+',
    re.IGNORECASE
)

# Known tech companies & normalization mapping
KNOWN_COMPANIES = {
    "devkiosk": "Devkiosk",
    "kavelogics": "KaveLogics",
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
    "devkiosk.com": "Devkiosk",
    "kavelogics.com": "KaveLogics",
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

INVALID_ROLE_WORDS = {
    "month", "months", "year", "years", "week", "weeks", "day", "days",
    "paid", "unpaid", "stipend", "pkr", "rs", "salary", "lpa",
    "converts to", "full-time", "part-time", "hybrid", "onsite", "on-site",
    "remote", "timings", "hours", "shift", "based on", "performance",
    "overview", "details", "description", "requirements", "responsibilities"
}

COMMON_ROLES = [
    "associate python engineer", "associate python developer", "junior python developer",
    "software engineering intern", "software engineer intern", "associate software engineer",
    "junior software engineer", "python developer intern", "python intern",
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
    """Cleans role title, strips leading numbers/bullets/emojis/arrows, normalizes plurals and acronyms."""
    # Strip leading bullets, emojis, keycaps, numbers with boxes, arrows, or dashes
    title = re.sub(r'^[\d\s\W→•\-\*\:\>]+', '', title.strip())
    title = title.rstrip(".,;:!?)'\"")

    # Plural to singular normalization
    title = re.sub(r'\bInterns\b', 'Intern', title, flags=re.IGNORECASE)
    title = re.sub(r'\bEngineers\b', 'Engineer', title, flags=re.IGNORECASE)
    title = re.sub(r'\bDevelopers\b', 'Developer', title, flags=re.IGNORECASE)
    title = re.sub(r'\bAssociates\b', 'Associate', title, flags=re.IGNORECASE)

    words = title.strip().split()
    formatted = []
    acronyms = {"qa": "QA", "sqa": "SQA", "ai": "AI", "api": "API", "ml": "ML", "se": "SE", "ase": "ASE", "swe": "SWE"}
    for w in words:
        w_clean = w.strip(".,;:!?)'\"")
        w_lower = w_clean.lower()
        if w_lower in acronyms:
            formatted.append(acronyms[w_lower])
        else:
            formatted.append(w_clean.capitalize())
    return " ".join(formatted)

def extract_requested_subject(text: str, candidate_name: str = CANDIDATE_NAME, fallback_role: str = "") -> Optional[str]:
    """Detects recruiter-mandated subject line templates and formats them with candidate name."""
    patterns = [
        # Subject: SE Intern – [Your Name]
        r'(?:Subject|Subject\s*line)[^\S\r\n]*[:\-][^\S\r\n]*([^\n\r]+)',
        # mention '...' in subject
        r'(?:mention(?:ing)?|with|use|keep)\s+["\'‘“]([^"\'’”\n\r]+)["\'’”]\s+(?:in|as)\s+(?:the\s+)?subject',
        # subject as '...'
        r'subject\s+(?:must\s+be|should\s+be|as)[^\S\r\n]*[:\-]?\s*["\'‘“]?([^"\'’”\n\r]+)["\'’”]?',
        # send CV with subject '...'
        r'send\s+(?:your\s+)?(?:cv|resume)\s+with\s+subject[^\S\r\n]*[:\-]?\s*["\'‘“]?([^"\'’”\n\r]+)["\'’”]?'
    ]

    for pat in patterns:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            raw_sub = m.group(1).strip().strip("'\"“”‘’")
            if not raw_sub or len(raw_sub) < 3:
                continue

            sub = raw_sub
            # Replace candidate name placeholders
            name_placeholders = [
                r'\[(?:Your\s*Name|Name|Full\s*Name|Candidate\s*Name)\]',
                r'<[^>]*name[^>]*>',
                r'\{(?:Your\s*Name|Name|Full\s*Name)\}',
                r'\b(?:Your\s*Name|Candidate\s*Name|Full\s*Name)\b',
                r'\[Candidate\]'
            ]
            has_name_placeholder = False
            for nh in name_placeholders:
                if re.search(nh, sub, flags=re.IGNORECASE):
                    sub = re.sub(nh, candidate_name, sub, flags=re.IGNORECASE)
                    has_name_placeholder = True

            # Replace role placeholders
            if fallback_role:
                sub = re.sub(r'\[(?:Role|Job\s*Title|Position)\]', fallback_role, sub, flags=re.IGNORECASE)

            # If no placeholder was used and candidate name not present, append name cleanly
            if not has_name_placeholder and candidate_name.lower() not in sub.lower():
                sub = f"{sub} - {candidate_name}"

            # Normalize dashes and whitespace
            sub = sub.replace("–", "-").replace("—", "-")
            sub = " ".join(sub.split())
            return sub

    return None

def _infer_role(text: str) -> str:
    """Extracts job title from text, avoiding duration, stipend, or contract text."""
    # Pattern 1: Check requested subject line for role hint (e.g. "Subject: SE Intern – [Your Name]" -> "SE Intern")
    sub_m = re.search(r'(?:Subject|Subject\s*line)[^\S\r\n]*[:\-][^\S\r\n]*([^\n\r]+)', text, flags=re.IGNORECASE)
    if sub_m:
        sub_candidate = sub_m.group(1).strip()
        part_role = re.split(r'[\-\–\—\[\<\{]', sub_candidate)[0].strip()
        if len(part_role) >= 2 and len(part_role) <= 40:
            if not any(bad in part_role.lower() for bad in INVALID_ROLE_WORDS):
                if any(k in part_role.lower() for k in ["intern", "engineer", "developer", "lead", "associate", "qa", "sqa", "architect", "trainee", "se", "ase"]):
                    return _clean_role_title(part_role)

    # Pattern 2: Headline / Opening announcement (e.g. "Hiring Software Engineering Interns in Lahore")
    headline = re.search(
        r'(?:Hiring|Urgent hiring|We are hiring|We\'re hiring|Looking for|Seeking)\s+(?:for\s+)?(?:an?\s+)?([A-Za-z\s/]{2,50}?\b(?:Engineers?|Developers?|Interns?|Specialists?|Consultants?|Architects?|Leads?|Associates?|Analysts?|Trainees?|Testers?)\b)',
        text,
        flags=re.IGNORECASE
    )
    if headline:
        val = headline.group(1).strip()
        if not any(bad in val.lower() for bad in INVALID_ROLE_WORDS):
            return _clean_role_title(val)

    # Pattern 3: Explicit same-line label (e.g. "Role: Python Developer", "Position: SE Intern")
    role_label = re.search(r'(?:Role|Position|Job Title|Title|Opening|Hiring for)[^\S\r\n]*[:\-][^\S\r\n]*([^\n\r,]+)', text, flags=re.IGNORECASE)
    if role_label:
        val = role_label.group(1).strip()
        if len(val) >= 3 and len(val) < 50:
            if not any(bad in val.lower() for bad in INVALID_ROLE_WORDS):
                return _clean_role_title(val)

    # Pattern 4: Standalone line or bullet containing a role title (e.g. "1️⃣ Business Development Interns")
    for line in text.splitlines():
        line_clean = line.strip()
        line_clean = re.sub(r'^[\d\s\W→•\-\*\:\>]+', '', line_clean).strip()
        m_line = re.search(r'\b([A-Za-z\s/]{2,45}?\b(?:Engineers?|Developers?|Interns?|Specialists?|Consultants?|Architects?|Leads?|Associates?|Analysts?|Trainees?|Testers?))\b', line_clean, flags=re.IGNORECASE)
        if m_line:
            val = m_line.group(1).strip()
            if len(val) >= 4 and not any(bad in val.lower() for bad in INVALID_ROLE_WORDS):
                return _clean_role_title(val)

    # Pattern 5: Check standard roles sorted by length
    text_lower = text.lower()
    for role in COMMON_ROLES:
        if re.search(r'\b' + re.escape(role) + r'\b', text_lower):
            return _clean_role_title(role)

    return "Software Engineer"

def _infer_location(text: str) -> str:
    """Detects Pakistani or remote tech hubs from text."""
    text_lower = text.lower()
    locs = []
    if "lahore" in text_lower or "johar town" in text_lower:
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

def parse_raw_job_post(raw_text: str, candidate_name: str = CANDIDATE_NAME) -> Dict[str, Any]:
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

    # 3. Extract recruiter-mandated subject line (e.g. 'SE Intern – Ahmad Faraz')
    subject_line = extract_requested_subject(raw_text, candidate_name=candidate_name, fallback_role=job_title)
    if not subject_line:
        subject_line = f"Application for {job_title} - {candidate_name}"

    # 4. Generate dynamic tailored pitch based on extracted parameters & actual tech stack
    pitch = generate_tailored_pitch(
        job_title=job_title,
        company=company,
        job_description=raw_text
    )

    return {
        "status": "SUCCESS",
        "company": company,
        "job_title": job_title,
        "subject_line": subject_line,
        "recruiter_email": primary_email,
        "discovered_emails": emails,
        "location": location,
        "tailored_pitch": pitch,
        "raw_text_length": len(raw_text)
    }
