"""
Dynamic Skills & AI Pitch Customizer for Ahmad Faraz.
Replaces rigid regex templates with deep contextual reasoning:
1. Uses direct Gemini REST API when GEMINI_API_KEY is configured.
2. Uses an advanced Semantic Domain Engine when running offline / local.
Strictly adheres to OUTREACH_GUIDELINES.md: zero emojis, authentic, humble, and persuasive.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Optional
import httpx

from config import Config

logger = logging.getLogger(__name__)

# Strict Zero-Emoji Filter for professional cold outreach
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
    """Strictly removes all emojis, dingbats, pictographs, and keycaps."""
    if not text:
        return ""
    return EMOJI_PATTERN.sub('', text)

def _generate_with_gemini_api(
    job_title: str,
    company: str,
    job_description: str
) -> Optional[str]:
    """Generates a bespoke pitch paragraph via direct Gemini REST API in <1 second."""
    api_key = getattr(Config, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return None

    prompt = (
        f"You are drafting the middle pitch paragraph of a cold application email for Ahmad Faraz.\n"
        f"Ahmad Faraz is a BS Software Engineering graduate with strong hands-on skills in Python (FastAPI, Django), "
        f"PostgreSQL, React, Playwright/Selenium test automation, and Agentic AI workflows.\n\n"
        f"Job Title: {job_title}\n"
        f"Company: {company}\n"
        f"Job Description / Snippet: {job_description[:800]}\n\n"
        f"Instructions:\n"
        f"1. Write EXACTLY one authentic paragraph (2 to 3 sentences, 50-80 words).\n"
        f"2. Focus specifically on how Ahmad's relevant Python/software engineering background directly contributes to {company}.\n"
        f"3. Strict ZERO EMOJIS (no emojis anywhere).\n"
        f"4. Humble, professional, direct developer voice (no corporate buzzwords like 'spearhead' or 'synergy').\n"
        f"5. Do NOT include greetings (Hello...) or sign-offs (Regards...); output ONLY the middle paragraph."
    )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 200}
    }

    try:
        with httpx.Client(timeout=4.0) as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        text = parts[0].get("text", "").strip()
                        return strip_all_emojis(text).strip()
    except Exception as e:
        logger.warning(f"[PitchCustomizer] Gemini API generation error: {e}. Falling back to semantic engine.")

    return None

def _generate_semantic_pitch(
    job_title: str,
    company: str,
    job_description: str = ""
) -> str:
    """Advanced local semantic synthesis engine that produces company-tailored pitches."""
    desc = f"{job_title} {company} {job_description}".lower()

    # Domain classification
    is_ai = bool(re.search(r'\b(ai|agent|llm|langchain|rag|model|machine learning|generative)\b', desc))
    is_fastapi = bool(re.search(r'\bfastapi\b', desc))
    is_django = bool(re.search(r'\bdjango\b', desc))
    is_react = bool(re.search(r'\b(react|next|frontend|ui)\b', desc))
    is_qa = bool(re.search(r'\b(qa|testing|automation|selenium|playwright|sqa)\b', desc))
    is_intern = bool(re.search(r'\b(intern|internship|trainee|fresh|graduate|entry)\b', desc))

    opening = f"I am reaching out regarding the {job_title} position at {company}."

    if is_ai:
        core = (
            f"{opening} As a Software Engineering graduate specializing in Python and Agentic AI workflows, "
            f"I have hands-on experience building autonomous tool-calling systems, integrating LLM APIs, and designing scalable backend architectures. "
            f"I would welcome the opportunity to contribute directly to {company}'s AI and automation engineering initiatives."
        )
    elif is_qa:
        core = (
            f"{opening} With hands-on experience in Python scripting, test automation (Playwright and Selenium), and REST API validation, "
            f"I bring a thorough, detail-oriented approach to debugging, catching regressions, and writing robust integration suites. "
            f"I am eager to contribute to maintaining top-tier software reliability across {company}'s engineering stack."
        )
    elif is_fastapi:
        core = (
            f"{opening} I have focused heavily on building high-performance asynchronous REST APIs with Python (FastAPI), "
            f"structured database schemas in PostgreSQL, and clean modular backend design. "
            f"I would be glad to bring my backend development skills and enthusiasm for fast execution to {company}'s development team."
        )
    elif is_django:
        core = (
            f"{opening} I have hands-on experience developing full-featured web applications using Python (Django), "
            f"designing relational database models, and building clean RESTful endpoints. "
            f"I am eager to apply my practical development foundation and rapid problem-solving to {company}'s ongoing projects."
        )
    elif is_react:
        core = (
            f"{opening} My background combines strong Python backend development with practical experience building modern, "
            f"responsive user interfaces in React. I enjoy connecting backend APIs with clean frontend states, "
            f"and I would love to support {company} as an adaptable, full-stack contributor."
        )
    elif is_intern:
        core = (
            f"{opening} As a motivated Software Engineering graduate with strong programming fundamentals in Python, "
            f"relational databases, and modern software development tools, I am eager to learn production-grade standards "
            f"and contribute actively to {company}'s engineering challenges."
        )
    else:
        core = (
            f"{opening} I have a solid foundation in Python backend engineering, database management, and building clean software workflows. "
            f"I take pride in writing readable, reliable code and would welcome the chance to add value to {company}'s software team."
        )

    return strip_all_emojis(core).strip()

def generate_tailored_pitch(
    job_title: str,
    company: str,
    job_description: str = "",
    notes: str = ""
) -> str:
    """Generates an organic, tailored pitch paragraph.
    Tries direct Gemini REST API first if configured, otherwise uses the Advanced Semantic Engine.
    """
    full_context = f"{job_description}\n{notes}".strip()

    # 1. Try Gemini API
    gemini_pitch = _generate_with_gemini_api(job_title, company, full_context)
    if gemini_pitch:
        return gemini_pitch

    # 2. Local Semantic Synthesis Engine
    return _generate_semantic_pitch(job_title, company, full_context)
