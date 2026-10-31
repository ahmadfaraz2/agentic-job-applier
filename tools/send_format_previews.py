"""
HTML Email Format Showcase.
Sends 4 distinct HTML layout styles to Ahmad Faraz's inbox for visual comparison.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import Config
from tools.email_tool import send_smtp_email, DEFAULT_CV_PATH

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

RECIPIENT = Config.ALERT_RECIPIENT_EMAIL or "user@example.com"
CV_ATTACHMENT = [str(DEFAULT_CV_PATH)] if DEFAULT_CV_PATH.exists() else None

# ==============================================================================
# FORMAT A: Native Gmail Minimalist (Authentic 1:1 Personal Email)
# ==============================================================================
# Looks 100% organic, exactly like typing directly in Gmail.
# Highest response rate from recruiters who reject marketing-style templates.
FORMAT_A_SUBJECT = "🎨 [Format A: Native Organic] Application for Associate Software Engineer — Ahmad Faraz"
FORMAT_A_HTML = """
<div style="font-family: Arial, Helvetica, sans-serif; font-size: 14.5px; color: #202124; line-height: 1.6; max-width: 600px;">
    <p style="margin: 0 0 16px 0;">Hello Rolustech team,</p>
    
    <p style="margin: 0 0 16px 0;">
        I saw the Associate Software Engineer opening at Rolustech and would like to apply. 
        I am a Software Engineering graduate with hands-on experience building web applications using 
        <strong>Python (Django & FastAPI)</strong> and <strong>React</strong>. I regularly work with 
        REST APIs, SQL databases, Git, and automated testing tools like Selenium and Playwright.
    </p>
    
    <p style="margin: 0 0 16px 0;">
        I enjoy debugging complex systems, building robust features across the full stack, and picking up 
        new engineering tools quickly. I am based in Sargodha and open to discussing relocation to Lahore 
        or remote arrangements as required.
    </p>
    
    <p style="margin: 0 0 24px 0;">
        I have attached my CV (<code>Ahmad_Faraz_CV.pdf</code>) for your review and would be glad to talk about 
        how my background can contribute to your team.
    </p>
    
    <div style="margin-top: 24px; padding-top: 12px; border-top: 1px solid #e0e0e0; color: #3c4043;">
        <p style="margin: 0; font-weight: bold; color: #202124;">Regards,</p>
        <p style="margin: 2px 0 0 0; font-size: 15px; font-weight: bold; color: #1a73e8;">Ahmad Faraz</p>
        <p style="margin: 2px 0 0 0; color: #5f6368;">Phone</p>
        <p style="margin: 4px 0 0 0;">
            <a href="https://www.linkedin.com/in/ahmad-faraz-/" style="color: #1a73e8; text-decoration: none;">LinkedIn</a> &bull; 
            <a href="https://github.com/ahmadfaraz2" style="color: #1a73e8; text-decoration: none;">GitHub</a>
        </p>
    </div>
</div>
"""

# ==============================================================================
# FORMAT B: Modern Tech Card (Subtle Container + Stack Tags)
# ==============================================================================
# Clean container with skill badges, soft borders, and highlighted key strengths.
FORMAT_B_SUBJECT = "🎨 [Format B: Modern Tech Card] Application for Associate Software Engineer — Ahmad Faraz"
FORMAT_B_HTML = """
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 620px; margin: 0 auto; padding: 24px; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; box-shadow: 0 2px 6px rgba(0,0,0,0.03);">
    <div style="border-left: 4px solid #2563eb; padding-left: 14px; margin-bottom: 20px;">
        <h2 style="margin: 0; font-size: 19px; color: #0f172a;">Application for Associate Software Engineer</h2>
        <p style="margin: 3px 0 0 0; color: #64748b; font-size: 13px;">Candidate: <strong>Ahmad Faraz</strong> &bull; Software Engineering Graduate</p>
    </div>

    <p style="font-size: 15px; color: #334155; line-height: 1.6; margin: 0 0 16px 0;">
        Hello <strong>Rolustech Team</strong>,
    </p>

    <p style="font-size: 14.5px; color: #334155; line-height: 1.6; margin: 0 0 16px 0;">
        I am writing to express my strong interest in joining your engineering team. I bring hands-on experience building production-ready Python services, responsive React frontends, and automated web workflows.
    </p>

    <!-- Key Skill Pills -->
    <div style="background-color: #f8fafc; border-radius: 8px; padding: 14px; margin-bottom: 18px; border: 1px solid #edf2f7;">
        <p style="margin: 0 0 8px 0; font-size: 12px; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 0.5px;">Core Technical Strengths</p>
        <div style="display: flex; flex-wrap: wrap; gap: 6px;">
            <span style="background: #e0f2fe; color: #0369a1; padding: 3px 10px; border-radius: 6px; font-size: 12px; font-weight: 600;">Python (Django / FastAPI)</span>
            <span style="background: #e0e7ff; color: #4338ca; padding: 3px 10px; border-radius: 6px; font-size: 12px; font-weight: 600;">React & JavaScript</span>
            <span style="background: #fef3c7; color: #b45309; padding: 3px 10px; border-radius: 6px; font-size: 12px; font-weight: 600;">REST APIs & SQL</span>
            <span style="background: #dcfce7; color: #15803d; padding: 3px 10px; border-radius: 6px; font-size: 12px; font-weight: 600;">Browser Automation (Playwright)</span>
        </div>
    </div>

    <p style="font-size: 14.5px; color: #334155; line-height: 1.6; margin: 0 0 20px 0;">
        I am based in Sargodha and open to discussing relocation to Lahore or remote arrangements. My complete CV is attached for your review.
    </p>

    <div style="padding-top: 16px; border-top: 1px solid #f1f5f9; display: flex; justify-content: space-between; align-items: center;">
        <div>
            <p style="margin: 0; font-weight: 700; color: #0f172a; font-size: 15px;">Ahmad Faraz</p>
            <p style="margin: 2px 0 0 0; color: #64748b; font-size: 13px;">Phone</p>
        </div>
        <div>
            <a href="https://www.linkedin.com/in/ahmad-faraz-/" style="display: inline-block; background: #0077b5; color: #ffffff; text-decoration: none; padding: 6px 12px; border-radius: 6px; font-size: 12px; font-weight: 600; margin-right: 6px;">LinkedIn</a>
            <a href="https://github.com/ahmadfaraz2" style="display: inline-block; background: #24292e; color: #ffffff; text-decoration: none; padding: 6px 12px; border-radius: 6px; font-size: 12px; font-weight: 600;">GitHub</a>
        </div>
    </div>
</div>
"""

# ==============================================================================
# FORMAT C: Executive Tech Showcase (Dark Slate Banner + Clean Highlights)
# ==============================================================================
# Polished executive header, ideal for senior engineering roles, AI, and startups.
FORMAT_C_SUBJECT = "🎨 [Format C: Executive Tech] Application for Associate Software Engineer — Ahmad Faraz"
FORMAT_C_HTML = """
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 620px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; border: 1px solid #cbd5e1; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
    <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: #ffffff; padding: 22px 24px;">
        <h1 style="margin: 0; font-size: 18px; font-weight: 700; letter-spacing: -0.2px;">Ahmad Faraz</h1>
        <p style="margin: 4px 0 0 0; color: #94a3b8; font-size: 13px;">Software Engineer &bull; Fullstack & AI Automation</p>
    </div>

    <div style="padding: 24px;">
        <p style="font-size: 15px; color: #1e293b; margin: 0 0 14px 0; font-weight: 600;">Hello Rolustech Team,</p>
        
        <p style="font-size: 14.5px; color: #334155; line-height: 1.6; margin: 0 0 16px 0;">
            I would like to apply for the <strong>Associate Software Engineer</strong> opening. As a Software Engineering graduate, I specialize in architecting dependable web services, database-backed APIs, and autonomous browser workflows.
        </p>

        <!-- 2 Column Highlights -->
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 18px;">
            <tr>
                <td style="width: 50%; padding: 12px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px 0 0 8px; vertical-align: top;">
                    <p style="margin: 0 0 4px 0; font-size: 13px; font-weight: 700; color: #2563eb;">Backend & Automation</p>
                    <p style="margin: 0; font-size: 12.5px; color: #64748b; line-height: 1.4;">Python, Django, FastAPI, PostgreSQL, Selenium, Playwright, LLM APIs.</p>
                </td>
                <td style="width: 50%; padding: 12px; background: #f8fafc; border: 1px solid #e2e8f0; border-left: none; border-radius: 0 8px 8px 0; vertical-align: top;">
                    <p style="margin: 0 0 4px 0; font-size: 13px; font-weight: 700; color: #059669;">Frontend & Tooling</p>
                    <p style="margin: 0; font-size: 12.5px; color: #64748b; line-height: 1.4;">JavaScript, React, Next.js, Git version control, Docker, REST architecture.</p>
                </td>
            </tr>
        </table>

        <p style="font-size: 14.5px; color: #334155; line-height: 1.6; margin: 0 0 20px 0;">
            I am based in Sargodha and fully prepared to discuss on-site relocation or remote work. My CV (<code>Ahmad_Faraz_CV.pdf</code>) is attached for your consideration.
        </p>

        <div style="margin-top: 24px; padding-top: 14px; border-top: 1px solid #e2e8f0; font-size: 13px; color: #475569;">
            <p style="margin: 0; font-weight: 700; color: #0f172a;">Ahmad Faraz</p>
            <p style="margin: 2px 0 0 0;">Phone | <a href="mailto:your_email@gmail.com" style="color: #2563eb; text-decoration: none;">your_email@gmail.com</a></p>
            <p style="margin: 4px 0 0 0;">
                <a href="https://www.linkedin.com/in/ahmad-faraz-/" style="color: #2563eb; text-decoration: none; font-weight: 500;">LinkedIn Profile</a> &bull; 
                <a href="https://github.com/ahmadfaraz2" style="color: #2563eb; text-decoration: none; font-weight: 500;">GitHub Repositories</a>
            </p>
        </div>
    </div>
</div>
"""

# ==============================================================================
# FORMAT D: Modern Minimalist Bulleted (The Tech Recruiter Favorite)
# ==============================================================================
# High readability, no large graphics, clean bullets, perfect on mobile screens.
FORMAT_D_SUBJECT = "🎨 [Format D: Clean Minimalist Bulleted] Application for Associate Software Engineer — Ahmad Faraz"
FORMAT_D_HTML = """
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; font-size: 15px; color: #1e293b; line-height: 1.6; max-width: 600px;">
    <p style="margin: 0 0 14px 0;">Hello <strong>Rolustech Team</strong>,</p>

    <p style="margin: 0 0 14px 0;">
        I saw your opening for the <strong>Associate Software Engineer</strong> position and would like to be considered. As a Software Engineering graduate, here is what I can immediately bring to your team:
    </p>

    <ul style="margin: 0 0 16px 0; padding-left: 20px; color: #334155;">
        <li style="margin-bottom: 6px;"><strong>Python & Full-Stack Development:</strong> Built backend APIs with Django & FastAPI, paired with dynamic React frontends.</li>
        <li style="margin-bottom: 6px;"><strong>Automation & Testing:</strong> Implemented browser automation and scraper workflows using Selenium and Playwright.</li>
        <li style="margin-bottom: 6px;"><strong>Modern AI Integration:</strong> Experience integrating LLM APIs and building agentic workflows for automated tasks.</li>
        <li style="margin-bottom: 6px;"><strong>Databases & Version Control:</strong> Strong foundation in relational SQL databases, API data pipelines, and Git collaborative workflows.</li>
    </ul>

    <p style="margin: 0 0 14px 0;">
        I'm based in Sargodha and open to discussing relocation or remote setups. I've attached my CV for your review and would love to chat if my background fits your current needs.
    </p>

    <div style="margin-top: 24px; padding-top: 14px; border-top: 2px solid #3b82f6; color: #334155;">
        <p style="margin: 0; font-weight: 600; color: #0f172a;">Regards,</p>
        <p style="margin: 2px 0 0 0; font-weight: 700; font-size: 16px; color: #0f172a;">Ahmad Faraz</p>
        <p style="margin: 2px 0 0 0; font-size: 14px; color: #475569;">Phone</p>
        <p style="margin: 4px 0 0 0; font-size: 13px;">
            <a href="https://www.linkedin.com/in/ahmad-faraz-/" style="color: #2563eb; text-decoration: none; font-weight: 500;">LinkedIn</a> &bull; 
            <a href="https://github.com/ahmadfaraz2" style="color: #2563eb; text-decoration: none; font-weight: 500;">GitHub</a>
        </p>
    </div>
</div>
"""

def dispatch_all_formats():
    print("=" * 65)
    print("  Dispatching 4 Distinct HTML Layout Formats to your Gmail...")
    print(f"  Recipient: {RECIPIENT}")
    print("=" * 65)

    formats = [
        ("Format A (Native Gmail Organic)", FORMAT_A_SUBJECT, FORMAT_A_HTML),
        ("Format B (Modern Tech Card)", FORMAT_B_SUBJECT, FORMAT_B_HTML),
        ("Format C (Executive Tech Showcase)", FORMAT_C_SUBJECT, FORMAT_C_HTML),
        ("Format D (Clean Minimalist Bulleted)", FORMAT_D_SUBJECT, FORMAT_D_HTML),
    ]

    for name, subject, html in formats:
        print(f"\n-> Sending {name}...")
        res = send_smtp_email(
            to_email=RECIPIENT,
            subject=subject,
            body_html=html,
            body_text=f"Ahmad Faraz Application ({name})",
            attachments=CV_ATTACHMENT
        )
        print(f"   Status: {res}")

    print("\n" + "=" * 65)
    print("  All 4 formats successfully sent! Check your Gmail inbox.")
    print("=" * 65)

if __name__ == "__main__":
    dispatch_all_formats()
