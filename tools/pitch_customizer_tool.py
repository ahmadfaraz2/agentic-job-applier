"""
Dynamic Skills Customizer for Ahmad Faraz.
Analyzes job requirements and tailors the middle pitch paragraph to emphasize
the exact relevant skills (Backend, Fullstack, QA/Automation, AI Tools/Agents)
while keeping Ahmad Faraz's authentic 100% organic, humble, and direct voice.
"""

from __future__ import annotations

import re
from typing import List, Optional

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

def generate_tailored_pitch(
    job_title: str,
    company: str,
    job_description: str = "",
    notes: str = ""
) -> str:
    """Generates an organic, tailored pitch paragraph highlighting Ahmad Faraz's relevant stack.
    Dynamically reflects the exact stack requested in the post (Django, Node.js, PostgreSQL, MongoDB,
    Cursor/AI tools, React, etc.) in a human, humble, and persuasive tone.

    Args:
        job_title: Position title (e.g. 'Software Engineering Intern', 'Associate Python Engineer').
        company: Company name (e.g. 'Devkiosk', 'Systems Limited').
        job_description: Job description text or snippet.
        notes: Optional custom notes or user-provided requirements.

    Returns:
        A concise, tailored pitch matching Ahmad Faraz's authentic sent emails.
    """
    desc_clean = f"{job_title} {company} {job_description} {notes}".lower()

    # Exact skill detections using regex word boundaries to avoid substring false positives (e.g. 'ai' in 'paid')
    has_django = bool(re.search(r'\bdjango\b', desc_clean))
    has_fastapi = bool(re.search(r'\bfastapi\b', desc_clean))
    has_python = bool(re.search(r'\bpython\b', desc_clean)) or has_django or has_fastapi
    has_node = bool(re.search(r'\b(node|node\.js|nodejs|express)\b', desc_clean))
    has_react = bool(re.search(r'\b(react|reactjs|next\.js|nextjs)\b', desc_clean))
    has_postgres = bool(re.search(r'\b(postgres|postgresql)\b', desc_clean))
    has_mongo = bool(re.search(r'\b(mongo|mongodb)\b', desc_clean))
    has_sql = bool(re.search(r'\b(sql|mysql)\b', desc_clean)) or has_postgres
    has_qa = bool(re.search(r'\b(qa|sqa|testing|selenium|playwright|test automation|cypress)\b', desc_clean))
    has_ai_tools = bool(re.search(r'\b(cursor|codex|claude code|copilot|ai tools)\b', desc_clean))
    has_ai_agents = bool(re.search(r'\b(ai agent|llm|langchain|rag|autonomous agents)\b', desc_clean))
    has_ownership = bool(re.search(r'\b(ownership|solo|hand-holding|self-driven|independent)\b', desc_clean))

    opening = f"I saw your {job_title} opening at {company} and would like to apply."

    # 1. Pure QA / Testing Track
    if has_qa and not has_django and not has_node and not has_ai_tools:
        qa_pitch = (
            f"{opening} I am a Software Engineering graduate with hands-on experience in Python scripting, "
            f"test automation (Playwright and Selenium), REST API testing, and Git. I have a meticulous eye for "
            f"debugging, discovering edge cases, and ensuring software reliability, and I would love to contribute "
            f"actively to {company}'s quality assurance."
        )
        return strip_all_emojis(qa_pitch).strip()

    # 2. Dynamic Tech Stack Clause
    tech_skills: List[str] = []
    if has_django and has_fastapi:
        tech_skills.append("Python (Django and FastAPI)")
    elif has_django:
        tech_skills.append("Python (Django)")
    elif has_fastapi:
        tech_skills.append("Python (FastAPI)")
    elif has_python:
        tech_skills.append("Python backend development")

    if has_node:
        tech_skills.append("Node.js architectures")

    if has_react:
        tech_skills.append("responsive React interfaces")

    # Databases
    dbs: List[str] = []
    if has_postgres:
        dbs.append("PostgreSQL")
    if has_mongo:
        dbs.append("MongoDB")
    elif has_sql and not has_postgres:
        dbs.append("relational databases (SQL)")

    db_str = ""
    if dbs:
        db_str = f" and working with databases like {' and '.join(dbs)}"

    # Modern AI tools & Developer workflow
    ai_tool_str = ""
    if has_ai_tools:
        ai_tool_str = ", alongside practical experience utilizing modern AI developer workflows (Cursor and Claude Code)"
    elif has_ai_agents:
        ai_tool_str = ", alongside hands-on work with AI agent pipelines and LLM orchestration"

    # Autonomy & Ownership closing
    closing_str = ""
    if has_ownership:
        closing_str = f" I take strong ownership of projects from design to debugging, work comfortably without hand-holding, and am keen to contribute to {company}'s engineering team."
    else:
        closing_str = f" I enjoy solving practical engineering problems with care and am keen to contribute to {company}'s engineering team."

    # Fallback if no specific stack was detected
    skills_joined = " and ".join(tech_skills) if tech_skills else "Python (Django/FastAPI) and REST APIs"

    pitch = (
        f"{opening} I am a Software Engineering graduate with hands-on experience building applications using "
        f"{skills_joined}{db_str}{ai_tool_str}.{closing_str}"
    )

    return strip_all_emojis(pitch).strip()
