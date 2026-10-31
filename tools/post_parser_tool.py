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

import json
import logging
import os
import re
import shutil
import subprocess
from typing import Any, Dict, List, Optional

from tools.pitch_customizer_tool import generate_tailored_pitch

logger = logging.getLogger(__name__)

CANDIDATE_NAME = "Ahmad Faraz"

# Strict Zero-Emoji Filter for professional cold outreach (OUTREACH_GUIDELINES.md)
EMOJI_PATTERN = re.compile(
    r'['
    r'\U00010000-\U0010ffff'  # Supplemental Symbols, Pictographs, Emoticons
    r'\u2600-\u27ff'          # Miscellaneous Symbols & Dingbats
    r'\u2300-\u23ff'          # Miscellaneous Technical
    r'\u2b50-\u2b55'          # Stars
    r'\u200d'                 # Zero-width joiner
    r'\ufe0e\ufe0f'           # Variation selectors
    r'\u20e3'                 # Combining enclosing keycap
    r']+',
    flags=re.UNICODE
)

def strip_all_emojis(text: str) -> str:
    """Strictly removes all emojis, dingbats, pictographs, and keycaps from text, preserving line breaks."""
    if not text:
        return ""
    return EMOJI_PATTERN.sub('', text)

EMAIL_REGEX = re.compile(
    r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+',
    re.IGNORECASE
)

# Known tech companies & normalization mapping
KNOWN_COMPANIES = {
    "devkiosk": "Devkiosk",
    "kavelogics": "KaveLogics",
    "tekdex": "TekDex",
    "tekdexinc": "TekDex",
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
    "tekdexinc.com": "TekDex",
    "tekdex.com": "TekDex",
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
    comp_verb = re.search(r'([A-Z][A-Za-z0-9&. ]{1,35}?)\s+(?:is looking for|is hiring|is seeking|announces|has openings)', text)
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

FLUFF_PREFIX_REGEX = re.compile(
    r'^\s*(?:enthusiastic\s+and\s+motivated|passionate\s+and\s+motivated|'
    r'enthusiastic|motivated|passionate|talented|dedicated|energetic|'
    r'dynamic|driven|seasoned|ambitious|experienced|fresh|seeking|'
    r'looking\s+for\s+(?:an?\s+)?|hiring\s+(?:for\s+)?(?:an?\s+)?)\s+',
    re.IGNORECASE
)

def _clean_role_title(title: str) -> str:
    """Cleans role title, strips leading numbers/bullets/emojis/arrows/fluff adjectives, normalizes plurals and acronyms."""
    # Strip leading bullets, emojis, keycaps, numbers with boxes, arrows, or dashes
    title = strip_all_emojis(title)
    title = re.sub(r'^[\d\s\W→•\-\*\:\>]+', '', title.strip())
    title = title.rstrip(".,;:!?)'\"")

    # Strip marketing and fluff adjectives (e.g. 'enthusiastic and motivated DevOps Intern' -> 'DevOps Intern')
    while FLUFF_PREFIX_REGEX.search(title):
        title = FLUFF_PREFIX_REGEX.sub('', title).strip()

    # Plural to singular normalization
    title = re.sub(r'\bInterns\b', 'Intern', title, flags=re.IGNORECASE)
    title = re.sub(r'\bEngineers\b', 'Engineer', title, flags=re.IGNORECASE)
    title = re.sub(r'\bDevelopers\b', 'Developer', title, flags=re.IGNORECASE)
    title = re.sub(r'\bAssociates\b', 'Associate', title, flags=re.IGNORECASE)

    words = title.strip().split()
    formatted = []
    acronyms = {
        "qa": "QA", "sqa": "SQA", "ai": "AI", "api": "API", "ml": "ML",
        "se": "SE", "ase": "ASE", "swe": "SWE", "devops": "DevOps",
        "sre": "SRE", "it": "IT", "ui": "UI", "ux": "UX", "hr": "HR"
    }
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
    text_clean = strip_all_emojis(text)
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
        m = re.search(pat, text_clean, flags=re.IGNORECASE)
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
            return strip_all_emojis(sub)

    return None

def _infer_role(text: str) -> str:
    """Extracts genuine job title from text using EMAIL_PLAYBOOK hierarchy."""
    text_clean = strip_all_emojis(text)

    # Priority 1: Explicit same-line label (e.g. "Position: DevOps Intern", "Role: Python Developer")
    role_label = re.search(r'(?:Position|Role|Job\s*Title|Title)[^\S\r\n]*[:\-][^\S\r\n]*([^\n\r,]+)', text_clean, flags=re.IGNORECASE)
    if role_label:
        val = role_label.group(1).strip()
        if len(val) >= 2 and len(val) < 50:
            if not any(bad in val.lower() for bad in INVALID_ROLE_WORDS):
                return _clean_role_title(val)

    # Priority 2: Check requested subject line for role hint (e.g. "Subject: SE Intern – [Your Name]" -> "SE Intern")
    sub_m = re.search(r'(?:Subject|Subject\s*line)[^\S\r\n]*[:\-][^\S\r\n]*([^\n\r]+)', text_clean, flags=re.IGNORECASE)
    if sub_m:
        sub_candidate = sub_m.group(1).strip()
        part_role = re.split(r'[\-\–\—\[\<\{]', sub_candidate)[0].strip()
        if len(part_role) >= 2 and len(part_role) <= 40:
            if not any(bad in part_role.lower() for bad in INVALID_ROLE_WORDS):
                if any(k in part_role.lower() for k in ["intern", "engineer", "developer", "lead", "associate", "qa", "sqa", "architect", "trainee", "se", "ase", "devops"]):
                    return _clean_role_title(part_role)

    # Priority 3: Standalone line or bullet containing a role title (e.g. "1️⃣ Business Development Interns")
    for line in text_clean.splitlines():
        line_clean = line.strip()
        line_clean = re.sub(r'^[\d\s\W→•\-\*\:\>]+', '', line_clean).strip()
        m_line = re.search(r'\b([A-Za-z\s/]{2,45}?\b(?:Engineers?|Developers?|Interns?|Specialists?|Consultants?|Architects?|Leads?|Associates?|Analysts?|Trainees?|Testers?))\b', line_clean, flags=re.IGNORECASE)
        if m_line:
            val = m_line.group(1).strip()
            if len(val) >= 4 and not any(bad in val.lower() for bad in INVALID_ROLE_WORDS):
                return _clean_role_title(val)

    # Priority 4: Headline / Opening announcement (e.g. "TekDex is Hiring | DevOps Interns")
    headline = re.search(
        r'(?:Hiring|Urgent hiring|We are hiring|We\'re hiring|Looking for|Seeking)\s*(?:\||\:)?\s*(?:for\s+)?(?:an?\s+)?([A-Za-z\s/]{2,50}?\b(?:Engineers?|Developers?|Interns?|Specialists?|Consultants?|Architects?|Leads?|Associates?|Analysts?|Trainees?|Testers?)\b)',
        text_clean,
        flags=re.IGNORECASE
    )
    if headline:
        val = headline.group(1).strip()
        if not any(bad in val.lower() for bad in INVALID_ROLE_WORDS):
            return _clean_role_title(val)

    # Priority 5: Check standard roles sorted by length
    text_lower = text_clean.lower()
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

def _get_agy_bin() -> Optional[str]:
    """Finds real agy binary path for model reasoning."""
    path = shutil.which("agy.exe") or shutil.which("agy")
    if path:
        return path
    candidates = [
        os.path.expanduser("~\\AppData\\Local\\agy\\bin\\agy.exe"),
        "C:\\Users\\ahmad\\AppData\\Local\\agy\\bin\\agy.exe",
        os.path.expanduser("~\\.gemini\\antigravity-cli\\bin\\agy.exe"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None

def _parse_with_antigravity_model(raw_text: str, candidate_name: str = CANDIDATE_NAME) -> Optional[Dict[str, Any]]:
    """Uses the authenticated Google Antigravity Gemini 3.8 Flash session to reason and extract job intelligence."""
    agy_bin = _get_agy_bin()
    if not agy_bin:
        return None

    prompt = f"""You are the Antigravity Executive Outreach Intelligence Engine for Ahmad Faraz (dev.ahmadfaraz24@gmail.com).
Your job is to read this raw hiring post, reason carefully, and extract structured job intelligence according to strict rules:

CRITICAL RULES:
1. STRICT ZERO EMOJIS: Never include emojis in company, job title, subject line, or pitch.
2. CANONICAL JOB TITLE: Extract the pure, corporate job title (e.g. 'DevOps Intern', 'Software Engineering Intern', 'Associate Python Engineer'). NEVER include marketing adjectives (e.g. 'Enthusiastic and Motivated'), bullet numbers ('1️⃣'), or contract duration ('2-3 month paid').
3. RECRUITER SUBJECT LINE: If the post specifies a subject template like 'Subject: SE Intern – [Your Name]', replace placeholders with '{candidate_name}'. If no subject is specified, format as: 'Application for [Job Title] - {candidate_name}'.
4. AUTHENTIC TAILORED PITCH: Ahmad Faraz is a BS Software Engineering graduate. He has practical hands-on experience in Python (Django, FastAPI), React, PostgreSQL, MongoDB, Playwright/Selenium test automation, Git/Linux, and modern AI coding tools (Cursor and Claude Code). Tailor the middle pitch paragraph (2-3 sentences, <100 words) specifically to the technologies mentioned in the post. Keep tone humble, authentic, direct, and organic.

Raw Post Text:
\"\"\"
{raw_text}
\"\"\"

Respond with ONLY a pure JSON object in this exact schema (no markdown fences, no conversational text, no tool calls):
{{
  "company": "Company Name",
  "job_title": "Clean Canonical Job Title",
  "recruiter_email": "recruiter@example.com",
  "location": "City or Remote",
  "subject_line": "Subject Line with {candidate_name} and ZERO emojis",
  "tailored_pitch": "Humble, tailored middle pitch paragraph with ZERO emojis"
}}
"""

    cmd = [
        agy_bin,
        "-p", prompt,
        "--output-format", "json",
        "--disable-slash-commands",
        "--dangerously-skip-permissions"
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=25)
        if proc.returncode != 0:
            logger.warning(f"Antigravity CLI returned code {proc.returncode}: {proc.stderr}")
            return None

        data = json.loads(proc.stdout.strip())
        response_text = data.get("response", "").strip()

        # Clean any accidental markdown fences
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        parsed_json = json.loads(response_text)

        # Validate required fields
        if not parsed_json.get("company") or not parsed_json.get("job_title"):
            return None

        # Sanitize zero-emojis
        company = " ".join(strip_all_emojis(parsed_json.get("company", "")).split())
        job_title = " ".join(strip_all_emojis(parsed_json.get("job_title", "")).split())
        recruiter_email = strip_all_emojis(parsed_json.get("recruiter_email", "")).strip().lower()
        location = " ".join(strip_all_emojis(parsed_json.get("location", "Pakistan / Remote")).split())
        subject_line = " ".join(strip_all_emojis(parsed_json.get("subject_line", f"Application for {job_title} - {candidate_name}")).split())
        pitch = strip_all_emojis(parsed_json.get("tailored_pitch", "")).strip()

        # Discovered emails fallback
        emails = _extract_emails(raw_text)
        if not recruiter_email and emails:
            recruiter_email = emails[0]
        elif recruiter_email and recruiter_email not in emails:
            emails.insert(0, recruiter_email)

        return {
            "status": "SUCCESS",
            "company": company,
            "job_title": job_title,
            "subject_line": subject_line,
            "recruiter_email": recruiter_email,
            "discovered_emails": emails,
            "location": location,
            "tailored_pitch": pitch,
            "model_engine": "Gemini 3.8 Flash (Antigravity Model Intelligence)",
            "raw_text_length": len(raw_text)
        }
    except Exception as e:
        logger.warning(f"Antigravity model parsing exception: {e}. Falling back to rule hierarchy.")
        return None

def parse_raw_job_post(raw_text: str, candidate_name: str = CANDIDATE_NAME) -> Dict[str, Any]:
    """Parses raw LinkedIn posts, emails, or job listings into structured data using Antigravity Gemini 3.8 Flash model."""
    raw_text = raw_text.strip()
    if not raw_text:
        return {"status": "ERROR", "message": "Raw post text is empty."}

    # 1. PRIMARY ENGINE: Antigravity Model Intelligence (Gemini 3.8 Flash via agy)
    model_result = _parse_with_antigravity_model(raw_text, candidate_name=candidate_name)
    if model_result and model_result.get("status") == "SUCCESS":
        return model_result

    # 2. EMERGENCY FALLBACK: Heuristic Rule Hierarchy (Guided by OUTREACH_GUIDELINES.md & EMAIL_PLAYBOOK.md)
    emails = _extract_emails(raw_text)
    primary_email = emails[0] if emails else ""

    company = " ".join(strip_all_emojis(_infer_company(raw_text, email_addr=primary_email)).split())
    job_title = " ".join(strip_all_emojis(_infer_role(raw_text)).split())
    location = " ".join(strip_all_emojis(_infer_location(raw_text)).split())

    subject_line = extract_requested_subject(raw_text, candidate_name=candidate_name, fallback_role=job_title)
    if not subject_line:
        subject_line = f"Application for {job_title} - {candidate_name}"
    subject_line = " ".join(strip_all_emojis(subject_line).split())

    pitch = strip_all_emojis(generate_tailored_pitch(
        job_title=job_title,
        company=company,
        job_description=raw_text
    ))

    return {
        "status": "SUCCESS",
        "company": company,
        "job_title": job_title,
        "subject_line": subject_line,
        "recruiter_email": primary_email,
        "discovered_emails": emails,
        "location": location,
        "tailored_pitch": pitch,
        "model_engine": "Emergency Rule Fallback",
        "raw_text_length": len(raw_text)
    }
