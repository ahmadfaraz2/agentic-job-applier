"""
Dynamic Skills Customizer for Ahmad Faraz.
Analyzes job requirements and tailors the middle pitch paragraph to emphasize
the exact relevant skills (Backend, Fullstack, QA/Automation, AI Agents)
while keeping Ahmad Faraz's authentic 100% organic, humble, and direct voice.
"""

from __future__ import annotations

import re
from typing import Optional

def generate_tailored_pitch(
    job_title: str,
    company: str,
    job_description: str = "",
    notes: str = ""
) -> str:
    """Generates an organic, tailored pitch paragraph highlighting Ahmad Faraz's relevant stack.

    Args:
        job_title: Position title (e.g. 'Associate Software Engineer', 'Python Intern').
        company: Company name (e.g. 'Rolustech', 'Contour Software').
        job_description: Job description text or snippet.
        notes: Optional custom notes or user-provided requirements.

    Returns:
        A concise, tailored pitch matching Ahmad Faraz's authentic sent emails.
    """
    combined_text = f"{job_title} {company} {job_description} {notes}".lower()

    # Detect technical focus areas
    is_qa_testing = any(w in combined_text for w in ["qa", "testing", "test", "sqa", "quality assurance", "selenium", "playwright", "cypress"])
    is_ai_agent = any(w in combined_text for w in ["ai", "agent", "llm", "langchain", "prompt", "machine learning", "rag"])
    is_frontend_fullstack = any(w in combined_text for w in ["react", "next.js", "frontend", "fullstack", "full stack", "javascript", "typescript", "ui"])
    is_backend = any(w in combined_text for w in ["backend", "django", "fastapi", "flask", "database", "sql", "postgres", "rest api", "api"])
    is_trainee_intern = any(w in combined_text for w in ["trainee", "intern", "internship", "fresh", "junior", "associate", "entry"])

    # 1. QA & Automation Testing track
    if is_qa_testing:
        return (
            f"I saw your {job_title} opening at {company} and wanted to apply. "
            f"I am a Software Engineering graduate with hands-on experience in Python scripting, test automation "
            f"(Playwright and Selenium), REST API testing, and Git. I have a meticulous eye for debugging, discovering "
            f"edge cases, and ensuring software reliability, and I would love to contribute actively to {company}'s quality assurance."
        )

    # 2. AI Agents & LLM Workflows track
    if is_ai_agent:
        return (
            f"I saw your {job_title} opening at {company} and would like to apply. "
            f"I am a Software Engineering graduate specializing in Python development, autonomous AI agent pipelines, "
            f"tool calling, and LLM orchestration, alongside hands-on experience with FastAPI, REST APIs, and databases. "
            f"I enjoy building practical automated workflows and am keen to contribute to your engineering initiatives."
        )

    # 3. Fullstack / React + Python track
    if is_frontend_fullstack and is_backend:
        return (
            f"I saw your {job_title} opening at {company} and would like to apply. "
            f"I am a Software Engineering graduate with practical experience building full-stack applications using Python "
            f"(Django and FastAPI) for backend services and React/JavaScript for clean, responsive interfaces. "
            f"I enjoy end-to-end problem solving and am eager to contribute to {company}'s product and development teams."
        )

    # 4. Frontend Focus
    if is_frontend_fullstack and not is_backend:
        return (
            f"I saw your {job_title} opening at {company} and wanted to apply. "
            f"I am a Software Engineering graduate with hands-on experience building dynamic web interfaces with React, "
            f"JavaScript, modern CSS, and integrating with RESTful backend APIs. I am detail-oriented with UI implementation "
            f"and would love the opportunity to contribute to {company}."
        )

    # 5. Backend / Python Focus
    if is_backend:
        return (
            f"I saw your {job_title} opening at {company} and wanted to apply. "
            f"I am a Software Engineering graduate with hands-on experience developing backend APIs in Python using "
            f"Django and FastAPI, working with relational databases (SQL/PostgreSQL), Git, and browser automation. "
            f"I enjoy designing reliable endpoints and debugging complex systems, and I am keen to contribute to {company}'s backend team."
        )

    # 6. Default / Trainee / Fresh Graduate General track
    return (
        f"I saw your {job_title} opening at {company} and would like to apply. "
        f"I am a Software Engineering graduate with hands-on experience building applications in Python (Django and FastAPI), "
        f"JavaScript/React, and AI Agent workflows, working with REST APIs, databases, Git, and automation scripting. "
        f"I am a fast learner with strong fundamentals and am eager to contribute actively to {company}'s engineering team."
    )
