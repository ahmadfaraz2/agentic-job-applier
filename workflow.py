"""
Antigravity SDK Autonomous Job Automation & SMTP Notification Workflow.
Orchestrates browser skills, HTTPX ingestion, qualification scoring, proposal generation,
and executive email digest delivery using the Google Antigravity SDK and Antigravity CLI session.
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

from config import Config
from tools.email_tool import send_smtp_email, send_cv_application_email
from tools.job_scanner_tool import scan_job_opportunities
from tools.tracker_tool import record_job_decision, get_application_history
from tools.browser_tool import browse_job_page, check_cdp_available, extract_job_and_email_from_url
from tools.web_search_tool import search_web_jobs, execute_prompt_search, parse_prompt_for_job_search
from antigravity_cli_agent import AntigravityCliAgent

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("AntigravityWorkflow")

SYSTEM_INSTRUCTIONS = """
You are Ahmad Faraz's Autonomous Job Application & Outreach Specialist.
Your mission is to represent Ahmad Faraz, Software Engineering graduate, discovering top opportunities, evaluating technical fit, and drafting or sending genuine, highly targeted application emails with his CV attached.

AHMAD FARAZ'S AUTHENTIC PROFILE & STYLE:
- Identity: Ahmad Faraz (Software Engineering graduate based in Sargodha, open to remote and relocation).
- Sender: Always 'Ahmad Faraz'. Never mention bot names.
- Core Stack: Python (Django, FastAPI), React, Next.js, JavaScript, REST APIs, SQL/PostgreSQL, Git, AI/LLM APIs & AI Agents, Browser Automation (Selenium, Playwright).
- Contact Info:
  * Location: Sargodha, Pakistan (Open to remote and relocation)
  * LinkedIn: https://www.linkedin.com/in/ahmad-faraz-/
  * GitHub: https://github.com/ahmadfaraz2
- Writing Style:
  * Greeting: "Hello [Company/Team name]," or "Dear [Hiring Manager],"
  * Body: 2 concise, honest paragraphs explaining relevant hands-on projects, stack fit, and problem-solving capability.
  * Location / Remote note: "I'm based in Sargodha and open to discussing remote work or relocation if needed."
  * Attached CV note: "I have attached my CV for your review and would be glad to talk about how I can contribute if my background is a match."
  * Sign-off:
    Regards,
    Ahmad Faraz
    LinkedIn: https://www.linkedin.com/in/ahmad-faraz-/
    GitHub: https://github.com/ahmadfaraz2

OPERATIONAL WORKFLOW:
1. Ingest opportunities via HTTPX and browser tools (`scan_job_opportunities`, `browse_job_page`).
2. Score technical match (0-100) based on Ahmad's real expertise.
3. For qualified leads, craft tailored proposals in Ahmad's natural voice and record decisions with `record_job_decision`.
4. Dispatch email digests or CV applications using `send_smtp_email` and `send_cv_application_email` with Ahmad_Faraz_CV.pdf attached.
"""

def get_registered_tools() -> dict:
    """Returns mapping of all agent tools."""
    return {
        "send_smtp_email": send_smtp_email,
        "send_cv_application_email": send_cv_application_email,
        "scan_job_opportunities": scan_job_opportunities,
        "search_web_jobs": search_web_jobs,
        "execute_prompt_search": execute_prompt_search,
        "browse_job_page": browse_job_page,
        "extract_job_and_email_from_url": extract_job_and_email_from_url,
        "record_job_decision": record_job_decision,
        "get_application_history": get_application_history,
    }

async def run_with_sdk_local_model(base_url: str = "http://localhost:11434/v1", model: str = "llama3") -> bool:
    """Runs the Antigravity SDK with a local OpenAI-compatible endpoint (NO API key needed)."""
    try:
        from google.antigravity import Agent, LocalOpenAIAgentConfig, types
    except ImportError:
        return False

    print("\n" + "=" * 65)
    print("  🚀 Launching Antigravity SDK Agent with Local Model (No API Key)")
    print(f"  Endpoint: {base_url} | Model: {model}")
    print("=" * 65 + "\n")

    tools_list = list(get_registered_tools().values())

    config = LocalOpenAIAgentConfig(
        model=model,
        base_url=base_url,
        system_instructions=SYSTEM_INSTRUCTIONS,
        tools=tools_list,
        capabilities=types.CapabilitiesConfig(
            agent_behavior=types.AgentBehavior.AUTONOMOUS
        ),
    ).lightweight()

    async with Agent(config) as agent:
        resp = await agent.chat("Run an immediate job sweep, qualify opportunities, and email the digest.")
        async for chunk in resp:
            sys.stdout.write(chunk)
            sys.stdout.flush()
    return True

async def run_unified_workflow() -> bool:
    """
    Main execution pipeline:
    - If user has local Ollama / LM Studio running: uses LocalOpenAIAgentConfig (no Gemini API key needed).
    - Uses AntigravityCliAgent bridge: runs autonomous agent powered by Gemini 3.8 Flash via active Google account (no Gemini API key needed).
    - If GEMINI_API_KEY is configured: uses LocalAgentConfig directly.
    """
    # Check if local OpenAI/Ollama is requested
    local_url = os.getenv("LOCAL_OPENAI_URL")
    if local_url:
        return await run_with_sdk_local_model(base_url=local_url, model=os.getenv("LOCAL_MODEL_NAME", "llama3"))

    # Check if GEMINI_API_KEY is available
    if Config.is_gemini_configured():
        try:
            from google.antigravity import Agent, LocalAgentConfig, types
            print("\n" + "=" * 65)
            print("  🚀 Launching Antigravity SDK Agent (Hosted Gemini)")
            print("=" * 65 + "\n")
            tools_list = list(get_registered_tools().values())
            config = LocalAgentConfig(
                model=Config.ANTIGRAVITY_MODEL,
                api_key=Config.GEMINI_API_KEY,
                system_instructions=SYSTEM_INSTRUCTIONS,
                tools=tools_list,
                capabilities=types.CapabilitiesConfig(
                    agent_behavior=types.AgentBehavior.AUTONOMOUS
                ),
            )
            async with Agent(config) as agent:
                resp = await agent.chat("Run an immediate job sweep, qualify opportunities, and email the digest.")
                async for chunk in resp:
                    sys.stdout.write(chunk)
                    sys.stdout.flush()
            return True
        except Exception as e:
            logger.warning(f"SDK Gemini launch failed ({e}), falling back to Antigravity CLI Agent...")

    # Default & Preferred Mode (Zero API key required):
    # Run autonomous agent through the active Antigravity CLI Google session
    agent = AntigravityCliAgent(
        system_instructions=SYSTEM_INSTRUCTIONS,
        tools=get_registered_tools(),
        model="Gemini 3.8 Flash (High)",
    )

    task = (
        f"Perform an autonomous job hunting cycle.\n"
        f"Search keywords: '{Config.JOB_SEARCH_QUERY}'\n"
        f"Minimum rate: ${Config.MIN_HOURLY_RATE}/hr\n"
        f"Remote only: {Config.REMOTE_ONLY}\n"
        f"Deliver email digest to: '{Config.ALERT_RECIPIENT_EMAIL or 'user@example.com'}'\n"
        f"Use HTTPX and browser tools to qualify leads and dispatch the digest via SMTP."
    )

    await agent.execute_autonomous_workflow(task)
    return True

async def start_periodic_daemon(interval_seconds: Optional[int] = None):
    """Starts the continuous background trigger daemon."""
    interval = interval_seconds or Config.SCAN_INTERVAL_SECONDS
    print("\n" + "=" * 65)
    print(f"  ⏰ Starting Background Job Automation Daemon (Interval: {interval}s)")
    print("  Press Ctrl+C to stop.")
    print("=" * 65 + "\n")

    while True:
        try:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Triggering automated job sweep...")
            await run_unified_workflow()
            print(f"Sleeping for {interval} seconds until next trigger...")
            await asyncio.sleep(interval)
        except (KeyboardInterrupt, asyncio.CancelledError):
            print("\nDaemon gracefully stopped.")
            break
        except Exception as e:
            logger.error(f"Error during periodic run: {e}", exc_info=True)
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(run_unified_workflow())
