"""
CLI Entrypoint for Agentic Job Automation & Organic Outreach Engine.
- Ingests copy-pasted jobs from user sources (data/pasted_jobs.json or direct CLI).
- Browses and extracts details/emails from any user-provided URL.
- Crawls live LinkedIn public jobs without authentication bottlenecks.
- Dispatches pure organic plain-text application emails with CV attached.
"""

from __future__ import annotations

import argparse
import asyncio
import io
import json
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

from config import Config
from test_smtp import run_smtp_test
from tools.tracker_tool import record_job_decision, get_application_history
from tools.browser_tool import browse_job_page, check_cdp_available, extract_job_and_email_from_url
from tools.email_tool import send_cv_application_email, get_cv_path, STANDARD_SIGNATURE_TEXT
from tools.job_scanner_tool import (
    fetch_linkedin_public_jobs,
    load_pasted_jobs,
    add_pasted_job,
    update_pasted_job_status
)
from tools.web_search_tool import execute_prompt_search, search_web_jobs
from tools.excel_tracker_tool import get_excel_stats, is_already_applied, EXCEL_FILE
from tools.post_parser_tool import parse_raw_job_post
from tools.inbox_listener_tool import check_inbound_recruiter_replies
from tools.discord_alert_tool import send_discord_notification
from workflow import run_unified_workflow, start_periodic_daemon

def print_banner():
    banner = f"""
    ╔══════════════════════════════════════════════════════════════╗
    ║        AGENTIC JOB APPLIER & OUTREACH ENGINE                 ║
    ║        Powered by Google Antigravity & Pure Organic SMTP     ║
    ║                         Version {Config.VERSION}                            ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def show_first_run_guide() -> bool:
    """Displays onboarding instructions when setup is missing, and offers the setup wizard.
    Returns True if user configured credentials, False if skipped.
    """
    print("\n" + "═" * 68)
    print("  🚀 WELCOME TO AGENTIC JOB APPLIER & OUTREACH ENGINE")
    print("═" * 68)
    print("  Before applying to jobs or starting the bot, please complete")
    print("  a quick 1-time setup for your Gmail and Discord.\n")
    print("  📧 1. GMAIL SETUP (Required for sending applications & tracking)")
    print("     • Set your Gmail address in SMTP_USER")
    print("     • Generate a 16-character Google App Password in SMTP_PASSWORD:")
    print("       1. Open: https://myaccount.google.com/security")
    print("       2. Ensure '2-Step Verification' is ON")
    print("       3. Search 'App passwords' (or https://myaccount.google.com/apppasswords)")
    print("       4. Create an App password and paste the 16 letters into .env")
    print("     • Set your name in SMTP_FROM_NAME (e.g. \"Jane Doe\")\n")
    print("  🤖 2. DISCORD BOT SETUP (Optional - apply via mobile DMs & screenshots)")
    print("     • Create an application at: https://discord.com/developers/applications")
    print("     • Under 'Bot' tab, copy Token into DISCORD_BOT_TOKEN")
    print("     • Under 'Privileged Gateway Intents', turn ON 'Message Content Intent'")
    print("     • In Discord: Settings > Advanced > Developer Mode (ON)")
    print("       Right-click your avatar > Copy User ID into DISCORD_OWNER_ID\n")
    print("  📄 3. YOUR CV RESUME")
    print("     • Place your resume in PDF format in the 'data/' folder")
    print("       (e.g., data/your_cv.pdf). Any .pdf file in data/ is auto-attached!\n")
    print("═" * 68)

    if sys.stdin and sys.stdin.isatty():
        try:
            choice = input("Would you like to run the interactive setup wizard right now? [Y/n]: ").strip().lower()
            if choice in ("", "y", "yes"):
                return run_interactive_setup()
        except (EOFError, KeyboardInterrupt):
            pass

    print("💡 To configure at any time, run:")
    print("   python run.py --setup\n")
    return False

def run_interactive_setup() -> bool:
    """Interactive CLI wizard to configure Gmail, Discord, and candidate info into .env."""
    print("\n" + "=" * 68)
    print("  🛠️  AGENTIC JOB APPLIER — INTERACTIVE SETUP WIZARD")
    print("=" * 68)
    print("Press Enter to keep the current/default value, or type a new one.\n")

    env_path = Config.BASE_DIR / ".env"
    existing_vars = {}
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if s and not s.startswith("#") and "=" in s:
                    k, v = s.split("=", 1)
                    existing_vars[k.strip()] = v.strip().strip('"').strip("'")

    # 1. Full Name
    curr_name = existing_vars.get("SMTP_FROM_NAME") or "Job Applicant"
    name = input(f"• Your Full Name [{curr_name}]: ").strip() or curr_name

    # 2. Gmail Address
    curr_email = existing_vars.get("SMTP_USER") or ""
    curr_email_display = f" [{curr_email}]" if curr_email else ""
    gmail = input(f"• Your Gmail Address{curr_email_display}: ").strip() or curr_email

    # 3. Google App Password
    curr_pass = existing_vars.get("SMTP_PASSWORD") or ""
    pass_display = " (hidden / already set)" if curr_pass and not curr_pass.startswith("your_") else ""
    print("  (Generate 16-letter App Password at https://myaccount.google.com/apppasswords)")
    app_pass = input(f"• Google App Password{pass_display}: ").strip() or curr_pass
    app_pass = app_pass.replace(" ", "")

    # 4. Discord Bot Token
    curr_token = existing_vars.get("DISCORD_BOT_TOKEN") or ""
    token_display = " (already set)" if curr_token and not curr_token.startswith("your_") else " (optional, press Enter to skip)"
    bot_token = input(f"• Discord Bot Token{token_display}: ").strip() or curr_token

    # 5. Discord Owner User ID
    curr_owner = existing_vars.get("DISCORD_OWNER_ID") or ""
    owner_display = f" [{curr_owner}]" if curr_owner else " (optional, press Enter to skip)"
    owner_id = input(f"• Discord User ID{owner_display}: ").strip() or curr_owner

    # Preserve webhook if present
    curr_webhook = existing_vars.get("DISCORD_WEBHOOK_URL", "")

    lines = [
        "# ==============================================================================",
        "# Agentic Job Applier & Organic Outreach Engine Configuration",
        "# ==============================================================================",
        "SMTP_HOST=smtp.gmail.com",
        "SMTP_PORT=587",
        "SMTP_USE_TLS=true",
        "SMTP_USE_SSL=false",
        f"SMTP_USER={gmail}",
        f"SMTP_PASSWORD={app_pass}",
        f"SMTP_FROM_EMAIL={gmail}",
        f'SMTP_FROM_NAME="{name}"',
        f"ALERT_RECIPIENT_EMAIL={gmail}",
        "",
        "# IMAP Inbound Reply Listener",
        "IMAP_HOST=imap.gmail.com",
        "IMAP_PORT=993",
        "",
        "# Discord Bot Configuration",
        f"DISCORD_BOT_TOKEN={bot_token}",
        f"DISCORD_OWNER_ID={owner_id}",
        f"DISCORD_WEBHOOK_URL={curr_webhook}",
        "",
        "# Job Search Preferences",
        "JOB_SEARCH_QUERY=Software Engineer",
        "SCAN_INTERVAL_SECONDS=3600",
    ]

    with open(env_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    Config.reload()

    print("\n" + "=" * 68)
    print("  ✅ CONFIGURATION SAVED TO .env")
    print("=" * 68)

    # Check for CV
    cv_file = get_cv_path()
    if cv_file:
        print(f"• CV Attachment Detected: {cv_file.name}")
    else:
        print("• ⚠️  No CV found yet. Please place your CV (.pdf) into:")
        print(f"     {Config.DATA_DIR}")

    print("\nQuick verification commands:")
    print("  • Test your Gmail SMTP: python run.py --test-smtp")
    print("  • Apply to a job post:  python run.py --paste")
    if bot_token:
        print("  • Start Discord Bot:    python run.py --discord-bot")
    print("=" * 68 + "\n")
    return True

def handle_paste_smart(to_email_arg: str = "", raw_post_text: str = ""):
    """Smart raw post parser and application dispatcher.
    Accepts full unformatted text from LinkedIn or any source, automatically extracts
    company, title, recruiter email, generates tailored pitch, checks deduplication,
    and dispatches with Ahmad_Faraz_CV.pdf attached.
    """
    raw_text = raw_post_text.strip()

    if not raw_text:
        # Check if text is piped via stdin
        if not sys.stdin.isatty():
            raw_text = sys.stdin.read().strip()

    if not raw_text:
        print("\n" + "=" * 65)
        print("  🚀 SMART RAW JOB POST PARSER (Powered by Antigravity)")
        print("=" * 65)
        print("Paste the complete raw LinkedIn post or hiring announcement below.")
        print("(Press Enter, then type 'EOF' or press Enter twice on empty line to finish):")
        print("-" * 65)

        lines = []
        empty_count = 0
        while True:
            try:
                line = input()
                if line.strip().upper() == "EOF":
                    break
                if line.strip() == "":
                    empty_count += 1
                    if empty_count >= 2 and lines:
                        break
                else:
                    empty_count = 0
                lines.append(line)
            except (EOFError, KeyboardInterrupt):
                break
        raw_text = "\n".join(lines).strip()

    if not raw_text:
        print("\n[!] Error: No post text provided.")
        return

    print("\n[Antigravity Engine] Analyzing post and extracting intelligence...")
    parsed = parse_raw_job_post(raw_text)

    if parsed.get("status") == "ERROR":
        print(f"[!] Error: {parsed.get('message')}")
        return

    company = parsed.get("company", "Company")
    job_title = parsed.get("job_title", "Software Engineer")
    location = parsed.get("location", "Pakistan / Remote")
    tailored_pitch = parsed.get("tailored_pitch", "")
    discovered_emails = parsed.get("discovered_emails", [])
    sender_name = getattr(Config, "SMTP_FROM_NAME", "") or "Job Applicant"
    subject_line = parsed.get("subject_line", f"Application for {job_title} - {sender_name}")

    # Recruiter email determination
    to_email = to_email_arg.strip()
    if not to_email and discovered_emails:
        to_email = discovered_emails[0]
    elif not to_email:
        to_email = input("\n• Recruiter email not found in post. Enter contact email (or press Enter to skip): ").strip()

    if not to_email:
        print("[!] No recipient email provided. Aborting application.")
        return

    # Check deduplication
    already_applied = is_already_applied(recipient_email=to_email, company=company, job_title=job_title)

    cv_file = get_cv_path()
    cv_display = cv_file.name if cv_file else "your_cv.pdf"
    cv_status = f"Available ({cv_display})" if cv_file else "Missing (add .pdf to data/)"

    print("\n" + "=" * 65)
    print("  [+] Extracted Job Intelligence (OUTREACH_GUIDELINES.md Active)")
    print("=" * 65)
    print(f"• Reasoning Engine: {parsed.get('model_engine', 'Gemini 3.8 Flash (Antigravity)')}")
    print(f"• Company:          {company}")
    print(f"• Job Title:        {job_title}")
    print(f"• Subject Line:     {subject_line}")
    print(f"• Recruiter Email:  {to_email}")
    if len(discovered_emails) > 1:
        print(f"• Other Emails:     {', '.join(discovered_emails[1:])}")
    print(f"• Location:         {location}")
    print(f"• CV Attachment:    {cv_display} ({cv_status})")
    print(f"• Duplicate Guard:  {'[ALREADY APPLIED IN TRACKER]' if already_applied else '[Clean - Never applied before]'}")
    print(f"• Zero-Emoji Rule:  Enforced (No emojis in subject, body, or headers)")
    print("-" * 65)
    print("[Tailored Email Outreach Preview - Pure Plain Text]")
    print("-" * 65)
    print(f"To: {to_email}")
    print(f"Subject: {subject_line}\n")
    print(f"Hello {company} team,\n")
    print(tailored_pitch)
    print("\nI'm based in Sargodha and open to discussing remote work or relocation if needed. I've attached my CV for your review and would be glad to talk about how I can contribute if my background is a match.\n")
    print(STANDARD_SIGNATURE_TEXT)
    print("=" * 65)

    if already_applied:
        force_prompt = input("\n[!] Duplicate detected. Do you want to FORCE send anyway? [y/N]: ").strip().lower()
        if force_prompt != "y":
            print("Application skipped to prevent duplicate emailing.")
            return

    action = input("\nSend application email NOW? [Y/n/q=Queue/e=Edit]: ").strip().lower()

    if action in ("", "y", "yes"):
        print(f"\n[Application Engine] Dispatching organic application to {to_email} with {cv_display}...")
        result = send_cv_application_email(
            to_email=to_email,
            job_title=job_title,
            company=company,
            custom_paragraph=tailored_pitch,
            custom_subject=subject_line,
            source_platform="LinkedIn Post",
            force=already_applied
        )
        print(f"Result: {result}")
        record_job_decision(
            job_id=f"paste_{abs(hash(to_email + job_title))}",
            job_title=job_title,
            company=company,
            action="APPLIED",
            match_score=95,
            notes=f"Applied via smart raw post paste to {to_email}"
        )
    elif action == "q":
        status_msg = add_pasted_job(
            to_email=to_email,
            job_title=job_title,
            company=company,
            source="LinkedIn Post (Smart Parsed)",
            notes=tailored_pitch,
            url=""
        )
        print(f"\n[✓] Queued: {status_msg}")
    elif action == "e":
        print("\n--- Quick Edit Mode ---")
        new_comp = input(f"• Company [{company}]: ").strip() or company
        new_title = input(f"• Job Title [{job_title}]: ").strip() or job_title
        new_email = input(f"• Recruiter Email [{to_email}]: ").strip() or to_email
        new_sub = input(f"• Subject Line [{subject_line}]: ").strip() or subject_line
        confirm = input(f"Send to {new_email} with subject '{new_sub}'? [Y/n]: ").strip().lower()
        if confirm in ("", "y", "yes"):
            result = send_cv_application_email(
                to_email=new_email,
                job_title=new_title,
                company=new_comp,
                custom_paragraph=tailored_pitch,
                custom_subject=new_sub,
                source_platform="LinkedIn Post",
                force=True
            )
            print(f"Result: {result}")
    else:
        print("Application aborted by user.")

def handle_apply_queue():
    """Iterates through all pending jobs in data/pasted_jobs.json and sends applications."""
    jobs = load_pasted_jobs()
    pending = [j for j in jobs if j.get("status") == "PENDING"]

    if not pending:
        print("\n[i] No pending jobs in data/pasted_jobs.json.")
        return

    print(f"\n[Queue] Found {len(pending)} pending job applications in queue:")
    print("-" * 60)
    for idx, j in enumerate(pending, 1):
        print(f"{idx}. {j.get('job_title')} at {j.get('company')} -> {j.get('to_email')}")
    print("-" * 60)

    confirm = input("Dispatch applications with CV attached to all pending jobs? [y/N]: ").strip().lower()
    if confirm != "y":
        print("Cancelled.")
        return

    for j in pending:
        to_email = j.get("to_email", "").strip()
        job_title = j.get("job_title", "Software Engineer").strip()
        company = j.get("company", "Company").strip()
        jid = j.get("id") or to_email

        print(f"\n[Sending] {job_title} at {company} to {to_email}...")
        res = send_cv_application_email(
            to_email=to_email,
            job_title=job_title,
            company=company,
            source_platform=j.get("source", "Pasted Queue")
        )
        print(f"Result: {res}")
        if "Success" in res:
            update_pasted_job_status(jid, status="APPLIED")
            record_job_decision(
                job_id=jid,
                job_title=job_title,
                company=company,
                action="APPLIED",
                match_score=95,
                notes=f"Applied via queue to {to_email}"
            )
    print("\n[✓] Completed queue processing.")

async def handle_apply_url(url: str, override_email: str = ""):
    """Inspects any web URL, extracts details/emails, drafts email, and sends with CV."""
    print(f"\n[Browser & Parser] Inspecting URL: {url}...")
    details = await extract_job_and_email_from_url(url)

    if details.get("status") == "ERROR":
        print(f"[!] Error inspecting URL: {details.get('message')}")
        return

    title = details.get("title", "Software Engineering Position")
    company = details.get("company", "Company")
    emails = details.get("emails", [])

    print("\n" + "=" * 60)
    print(f"• Extracted Title:   {title}")
    print(f"• Extracted Company: {company}")
    print(f"• Discovered Emails: {', '.join(emails) if emails else 'None detected automatically'}")
    print("=" * 60)

    # Determine recipient email
    target_email = override_email.strip()
    if not target_email and emails:
        target_email = emails[0]
        print(f"[i] Using detected email: {target_email}")
    elif not target_email:
        target_email = input("• Enter recruiter/hiring contact email: ").strip()

    if not target_email:
        print("[!] No recipient email provided. Aborting application.")
        return

    cv_file = get_cv_path()
    cv_display = cv_file.name if cv_file else "your_cv.pdf"

    print("\n[Application Preview]")
    print("-" * 60)
    preview_body = f"""Hello {company} team,

I saw the {title} opening at {company} and would like to apply. I'm a Software Engineering graduate with hands-on experience building Python (Django/FastAPI), JavaScript/React, and AI Agent applications, working with REST APIs, databases, Git, and browser automation (Selenium & Playwright). I enjoy debugging complex systems with care and am keen to contribute to your engineering team.

I'm based in Sargodha and open to discussing remote work or relocation if needed. I've attached my CV for your review and would be glad to talk about how I can contribute if my background is a match.

{STANDARD_SIGNATURE_TEXT}
"""
    print(preview_body)
    print("-" * 60)

    confirm = input(f"Dispatch this email with {cv_display} attached? [y/N]: ").strip().lower()
    if confirm == "y":
        res = send_cv_application_email(
            to_email=target_email,
            job_title=title,
            company=company,
            source_platform="URL Direct"
        )
        print(f"\nResult: {res}")
        record_job_decision(
            job_id=f"url_{abs(hash(url))}",
            job_title=title,
            company=company,
            action="APPLIED",
            match_score=95,
            notes=f"Applied via direct URL: {url}"
        )
    else:
        print("Application aborted.")

def handle_prompt_search(prompt_text: str = "", override_email: str = ""):
    """Takes a natural language prompt, runs live web & internship search, and allows interactive application."""
    prompt = prompt_text.strip()
    if not prompt:
        print("\n" + "=" * 60)
        print("  🔍 Prompt-Based Web Job & Internship Search")
        print("=" * 60)
        prompt = input("• Enter your job search prompt (e.g. 'search for jobs in lahore, Islamabad about internships and jobs'): ").strip()

    if not prompt:
        print("[!] No search prompt entered.")
        return

    print(f"\n[Web & Job Search] Executing search for: '{prompt}'...")
    results = execute_prompt_search(prompt, limit_per_query=4)

    if not results:
        print("\n[i] No live postings found matching that query.")
        return

    print(f"\nFound {len(results)} live opportunities from web search:\n" + "=" * 65)
    for idx, r in enumerate(results, 1):
        print(f"{idx}. [{r.get('source')}] {r.get('title')}")
        print(f"   Location: {r.get('location')}")
        print(f"   Link:     {r.get('url')}")
        if r.get('snippet'):
            clean_snip = ' '.join(r.get('snippet', '').split())[:120]
            print(f"   Snippet:  {clean_snip}...")
        print("-" * 65)

    choice = input("\nEnter opportunity number to inspect / apply (or press Enter to exit): ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(results):
        selected = results[int(choice) - 1]
        asyncio.run(handle_apply_url(selected["url"], override_email=override_email))

def main():
    print_banner()

    parser = argparse.ArgumentParser(
        description="Agentic Job Applier & Organic Outreach Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--setup",
        action="store_true",
        help="Run the interactive first-time setup wizard to configure Gmail and Discord.",
    )
    group.add_argument(
        "--scan",
        action="store_true",
        help="Execute an autonomous job sweep, qualification, and SMTP digest dispatch.",
    )
    group.add_argument(
        "--paste",
        action="store_true",
        help="Paste a complete raw LinkedIn post to automatically extract details, draft pitch, and dispatch.",
    )
    group.add_argument(
        "--post",
        type=str,
        metavar="TEXT",
        help="Pass raw LinkedIn/hiring post text directly to automatically extract, draft, and dispatch.",
    )
    group.add_argument(
        "--post-file",
        type=str,
        metavar="FILEPATH",
        help="Read raw LinkedIn post from a file to automatically extract, draft, and dispatch.",
    )
    group.add_argument(
        "--apply-queue",
        action="store_true",
        help="Dispatch application emails with CV attached to all pending jobs in data/pasted_jobs.json.",
    )
    group.add_argument(
        "--apply-url",
        type=str,
        metavar="URL",
        help="Inspect any job URL, extract details & emails, draft organic email, and send with CV.",
    )
    group.add_argument(
        "--daemon",
        action="store_true",
        help="Run continuously in the background on a scheduled interval.",
    )
    group.add_argument(
        "--test-smtp",
        action="store_true",
        help="Validate SMTP server credentials and send a test message.",
    )
    group.add_argument(
        "--test-cv",
        action="store_true",
        help="Send a test application email with your CV attached to your own inbox to preview formatting.",
    )
    group.add_argument(
        "--browse",
        type=str,
        metavar="URL",
        help="Use the Browser Agent skill to inspect a specific job URL via HTTPX.",
    )
    group.add_argument(
        "--linkedin",
        type=str,
        metavar="KEYWORDS",
        help="Search live LinkedIn public job openings (e.g. --linkedin 'Python' --location 'Lahore').",
    )
    group.add_argument(
        "--prompt",
        type=str,
        nargs="?",
        const="",
        metavar="PROMPT",
        help="Search the web for jobs/internships via natural prompt (e.g. --prompt 'search for jobs in lahore, Islamabad about internships and jobs').",
    )
    group.add_argument(
        "--search",
        type=str,
        metavar="QUERY",
        help="Search the web directly for specific job or internship queries.",
    )
    group.add_argument(
        "--history",
        action="store_true",
        help="Display the database history of evaluated opportunities and stats.",
    )
    group.add_argument(
        "--tracker",
        action="store_true",
        help="View applied jobs statistics and Excel tracker file details.",
    )
    group.add_argument(
        "--check-replies",
        action="store_true",
        help="Check Gmail inbox for recruiter responses, classify interviews/tests, and update Excel & Discord.",
    )
    group.add_argument(
        "--test-discord",
        action="store_true",
        help="Send a test notification to your configured Discord webhook.",
    )
    group.add_argument(
        "--discord-bot",
        action="store_true",
        help="Launch the interactive Discord bot to apply to jobs by pasting posts in Discord DMs.",
    )
    group.add_argument(
        "--reset-db",
        action="store_true",
        help="Clear the local jobs database to re-evaluate opportunities.",
    )

    parser.add_argument(
        "--to",
        type=str,
        default="",
        help="Target recipient email override for --apply-url or --test-cv.",
    )
    parser.add_argument(
        "--location",
        type=str,
        default="Pakistan",
        help="Location filter for LinkedIn jobs (default: 'Pakistan' or 'Remote').",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=Config.SCAN_INTERVAL_SECONDS,
        help=f"Daemon polling interval in seconds (default: {Config.SCAN_INTERVAL_SECONDS}s).",
    )

    args = parser.parse_args()

    if args.setup:
        run_interactive_setup()
        return

    # Check if this command requires SMTP configuration
    smtp_exempt_flags = [
        args.browse,
        args.linkedin,
        args.prompt is not None,
        args.search,
        args.history,
        args.tracker,
        args.reset_db,
    ]
    requires_smtp = not any(smtp_exempt_flags)

    if requires_smtp and not Config.is_smtp_configured():
        configured = show_first_run_guide()
        if not configured or not Config.is_smtp_configured():
            return

    if args.test_smtp:
        run_smtp_test()
        return

    if args.test_cv:
        recipient = args.to.strip() or Config.ALERT_RECIPIENT_EMAIL
        if not recipient:
            print("[!] Please set ALERT_RECIPIENT_EMAIL in .env or pass --to <email>")
            return
        cv_file = get_cv_path()
        cv_name = cv_file.name if cv_file else "your_cv.pdf"
        print(f"\n[Application Engine] Dispatching preview CV application to {recipient} with {cv_name}...")
        result = send_cv_application_email(
            to_email=recipient,
            job_title="Associate Software Engineer",
            company="Rolustech",
            custom_paragraph=(
                "I saw your Associate Software Engineer opening and would like to apply. "
                "I'm a Software Engineering graduate with hands-on experience building Python (Django/FastAPI), "
                "JavaScript/React, and AI Agent applications, working with REST APIs, databases, Git, and "
                "browser automation (Selenium & Playwright). I enjoy debugging complex systems with care and "
                "am keen to contribute to your engineering team."
            )
        )
        print(f"Result: {result}\n")
        return

    if args.post:
        handle_paste_smart(to_email_arg=args.to, raw_post_text=args.post)
        return

    if args.post_file:
        p = Path(args.post_file)
        if not p.exists():
            print(f"[!] Error: File '{args.post_file}' does not exist.")
            return
        content = p.read_text(encoding="utf-8", errors="replace")
        handle_paste_smart(to_email_arg=args.to, raw_post_text=content)
        return

    if args.paste:
        handle_paste_smart(to_email_arg=args.to)
        return

    if args.apply_queue:
        handle_apply_queue()
        return

    if args.apply_url:
        asyncio.run(handle_apply_url(args.apply_url, override_email=args.to))
        return

    if args.browse:
        print(f"\n[Browser Agent] Inspecting URL via HTTPX: {args.browse}\n")
        content = asyncio.run(browse_job_page(args.browse))
        print(content)
        return

    if args.linkedin:
        print(f"\n[LinkedIn Crawler] Discovering live jobs: '{args.linkedin}' in '{args.location}'...\n")
        jobs = fetch_linkedin_public_jobs(query=args.linkedin, location=args.location, limit=10)
        print(f"Found {len(jobs)} live LinkedIn opportunities:\n" + "-" * 60)
        for idx, j in enumerate(jobs, 1):
            print(f"{idx}. {j['title']} at {j['company']}")
            print(f"   Location: {j['location']}")
            print(f"   Link:     {j['url']}")
            print("-" * 60)

        # Allow user to inspect or apply right from CLI
        choice = input("\nEnter job number to inspect / apply (or press Enter to exit): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(jobs):
            selected = jobs[int(choice) - 1]
            asyncio.run(handle_apply_url(selected["url"], override_email=args.to))
        return

    if args.prompt is not None:
        handle_prompt_search(prompt_text=args.prompt, override_email=args.to)
        return

    if args.search:
        handle_prompt_search(prompt_text=args.search, override_email=args.to)
        return

    if args.reset_db:
        if Config.DB_FILE.exists():
            Config.DB_FILE.unlink()
            print(f"[✓] Cleared database file: {Config.DB_FILE}")
        else:
            print("[i] Database file does not exist yet.")
        return

    if args.history:
        history_json = get_application_history(limit=20)
        data = json.loads(history_json)
        stats = data.get("stats", {})
        print(f"Total Evaluated: {stats.get('total_evaluated', 0)}")
        print(f"Qualified:       {stats.get('qualified', 0)}")
        print(f"Rejected:        {stats.get('rejected', 0)}")
        print("-" * 60)
        for job in data.get("recent_jobs", []):
            print(f"[{job.get('status')}] {job.get('title')} ({job.get('company')}) - Score: {job.get('match_score')}")
        return

    if args.tracker:
        stats = get_excel_stats()
        print("\n" + "=" * 60)
        print("  📊 Excel Application Tracker Summary")
        print("=" * 60)
        print(f"• Total Applications Recorded: {stats.get('total_applications', 0)}")
        print(f"• Interview Invites Detected:  {stats.get('interview_invites', 0)}")
        print(f"• Unique Companies:            {stats.get('unique_companies', 0)}")
        print("• Applied Companies:")
        for c in stats.get("companies", []):
            print(f"   - {c}")
        print(f"\n• Excel File Path:\n  {stats.get('excel_path')}")
        print("=" * 60 + "\n")
        return

    if args.check_replies:
        print("\n" + "=" * 60)
        print("  📬 Inbound Recruiter Reply & Interview Detector")
        print("=" * 60)
        print("[IMAP] Scanning Gmail inbox for responses from applied companies...")
        replies = check_inbound_recruiter_replies(limit=30, notify_discord=True)
        if not replies:
            print("[i] No new replies from applied companies detected yet.")
        else:
            print(f"\n[✓] Detected {len(replies)} recruiter response(s):\n" + "-" * 60)
            for r in replies:
                print(f"• Company:  {r['company']}")
                print(f"  Category: {r['classification']}")
                print(f"  Subject:  {r['subject']}")
                print(f"  Snippet:  {r['snippet']}")
                print("-" * 60)
            print("[✓] Updated Excel tracker status and dispatched Discord alerts (if enabled).\n")
        return

    if args.test_discord:
        print("\n[Discord Alert] Dispatching test notification to configured webhook...")
        if not Config.DISCORD_WEBHOOK_URL:
            print("[!] Error: DISCORD_WEBHOOK_URL is not set in your .env file.")
            print("    Add: DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your/webhook/url")
            return
        sender_name = getattr(Config, "SMTP_FROM_NAME", "") or "Job Outreach"
        success = send_discord_notification(
            title=f"🔔 {sender_name} Outreach Bot — Test Alert",
            description="Your Discord real-time notification integration is active and working properly!",
            fields=[
                {"name": "Status", "value": "🟢 Connected & Live", "inline": True},
                {"name": "Engine", "value": "Google Antigravity SDK", "inline": True},
            ],
            color=0x22C55E
        )
        if success:
            print("[✓] Success! Check your Discord channel for the notification.\n")
        else:
            print("[!] Failed to deliver Discord webhook. Please verify the URL.\n")
        return

    if args.discord_bot:
        from discord_bot import run_bot, start_bot_async
        if args.daemon:
            async def _run_combined():
                await asyncio.gather(
                    start_periodic_daemon(interval_seconds=args.interval),
                    start_bot_async()
                )
            asyncio.run(_run_combined())
        else:
            run_bot()
        return

    if args.daemon:
        asyncio.run(start_periodic_daemon(interval_seconds=args.interval))
        return

    # Default: Run unified workflow
    asyncio.run(run_unified_workflow())

if __name__ == "__main__":
    main()
