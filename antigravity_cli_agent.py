"""
Antigravity CLI Agent Bridge.
Enables running autonomous Antigravity agents powered by Gemini 3.8 Flash
using your existing authenticated Google Antigravity session (via `agy` CLI)
WITHOUT requiring a separate Gemini API Key.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("AntigravityCliAgent")

def get_agy_path() -> Optional[str]:
    """Finds the agy CLI binary in PATH."""
    path = shutil.which("agy") or shutil.which("agy.exe")
    if path:
        return path
    candidates = [
        os.path.expanduser("~/.gemini/antigravity-cli/bin/agy.exe"),
        os.path.expanduser("~/scoop/apps/antigravity-cli/current/agy.exe"),
        os.path.expanduser("~/scoop/shims/agy.exe"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None

class AntigravityCliAgent:
    """Autonomous agent that leverages the authenticated Antigravity CLI session."""

    def __init__(
        self,
        system_instructions: str,
        tools: Optional[Dict[str, Callable]] = None,
        model: str = "Gemini 3.8 Flash",
        timeout_seconds: int = 25,
    ):
        self.system_instructions = system_instructions
        self.tools = tools or {}
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.agy_bin = get_agy_path()

    def has_agy(self) -> bool:
        return bool(self.agy_bin)

    async def run_prompt_with_agy(self, prompt: str) -> str:
        """Executes a prompt against the agy CLI without requiring a Gemini API key."""
        if not self.agy_bin:
            raise RuntimeError("Antigravity CLI ('agy') not found in PATH.")

        clean_prompt = (
            "CRITICAL OPERATIONAL CONSTRAINT:\n"
            "You are an autonomous JSON extraction and planning engine.\n"
            "DO NOT CALL ANY TOOLS (no view_file, no run_command, no search_web, no manage_task).\n"
            "You ALREADY have all the information and context you need in this prompt.\n"
            "Return ONLY valid JSON matching the requested schema. No conversational prose, no markdown fences, no tools.\n\n"
            f"{prompt}"
        )

        cmd = [
            self.agy_bin,
            "-p", clean_prompt,
            "--output-format", "json",
            "--disable-slash-commands",
            "--dangerously-skip-permissions",
            "--print-timeout", f"{self.timeout_seconds}s"
        ]

        logger.info(f"Invoking Antigravity CLI reasoning ({self.model})...")

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self.timeout_seconds + 5)
        except asyncio.TimeoutError:
            proc.kill()
            raise TimeoutError(f"Antigravity CLI timed out after {self.timeout_seconds}s.")

        raw_output = stdout.decode("utf-8", errors="replace").strip()
        if not raw_output:
            raw_err = stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"Antigravity CLI returned empty output. Stderr: {raw_err}")

        # Extract JSON from potential CLI envelope
        try:
            data = json.loads(raw_output)
            candidate = (
                data.get("response")
                or data.get("result")
                or data.get("output_text")
                or data.get("output")
                or data.get("content")
            )
            if candidate:
                return str(candidate)
        except Exception:
            pass

        return raw_output

    async def execute_autonomous_workflow(self, task_description: str) -> Dict[str, Any]:
        """Runs an autonomous multi-step cycle using tools, browser skills, and Antigravity reasoning."""
        print("\n" + "=" * 65)
        print("  🤖 Running Autonomous Agent via Antigravity CLI Session")
        print("  (Zero Gemini API key required - using active Google account)")
        print("=" * 65)

        # Step 1: Ingest via HTTPX & Browser Tools
        print("\n[1/4] Ingesting jobs via HTTPX & Browser Tools...")
        scan_fn = self.tools.get("scan_job_opportunities")
        raw_jobs_json = scan_fn() if scan_fn else "{}"
        jobs_data = json.loads(raw_jobs_json)
        discovered_jobs = jobs_data.get("jobs", [])

        print(f"      Retrieved {len(discovered_jobs)} fresh opportunities from live feeds.")

        if not discovered_jobs:
            print("      All discovered opportunities have already been processed and tracked.")
            return {"status": "SUCCESS", "processed": 0, "qualified": 0}

        # Step 2: Batch Qualification & Scoring
        print("\n[2/4] Qualifying candidate fit, scoring matches, and drafting pitches...")
        
        # Prepare batch payload for model
        batch_summary = []
        for j in discovered_jobs:
            batch_summary.append({
                "id": j["id"],
                "title": j["title"],
                "company": j["company"],
                "rate": j.get("rate", "N/A"),
                "tags": j.get("tags", [])[:5],
                "description": j.get("description", "")[:250]
            })

        batch_prompt = (
            f"You are an expert AI Job Recruiter. Evaluate these {len(batch_summary)} opportunities for an "
            f"Autonomous Python & AI Agent Engineer. Return JSON with key 'evaluations' as an array of objects: "
            f'[{{"id": "...", "score": <0-100>, "qualified": <bool>, "pitch": "<2 sentences tailored pitch>"}}].\n\n'
            f"Opportunities:\n{json.dumps(batch_summary, indent=2)}"
        )

        eval_map = {}
        try:
            res_str = await self.run_prompt_with_agy(batch_prompt)
            s = res_str.find("{")
            e = res_str.rfind("}")
            if s != -1 and e != -1:
                parsed = json.loads(res_str[s:e+1])
                for item in parsed.get("evaluations", []):
                    eval_map[item.get("id")] = item
        except Exception as e:
            logger.info(f"Antigravity CLI batch query skipped ({e}). Using expert heuristic evaluator.")

        qualified = []
        track_fn = self.tools.get("record_job_decision")

        for job in discovered_jobs:
            jid = job["id"]
            title = job["title"]
            company = job["company"]
            rate = job.get("rate", "N/A")
            desc = job.get("description", "")
            tags = " ".join(job.get("tags", []))
            is_remote = job.get("is_remote", False)

            # Check if LLM returned evaluation
            if jid in eval_map:
                score = int(eval_map[jid].get("score", 80))
                pitch = eval_map[jid].get("pitch", "")
            else:
                score = 50
                if is_remote:
                    score += 20
                if any(k in f"{title} {tags} {desc}".lower() for k in ["python", "ai", "agent", "llm", "automation", "httpx"]):
                    score += 25
                if job.get("budget", 0) >= 1000:
                    score += 15

                pitch = (
                    f"Hi {company} team, I noticed your listing for '{title}'. Having built autonomous "
                    f"multi-agent pipelines using Python, HTTPX browser skills, and background task "
                    f"orchestration, I can rapidly deliver a production-ready solution that exceeds requirements."
                )

            status = "QUALIFIED" if score >= 75 else "REJECTED"
            if status == "QUALIFIED":
                qualified.append({**job, "match_score": min(score, 100), "pitch": pitch})

            if track_fn:
                track_fn(
                    job_id=jid,
                    title=title,
                    company=company,
                    status=status,
                    match_score=min(score, 100),
                    pitch=pitch
                )
            print(f"      -> [{status}] {title} at {company} (Score: {min(score, 100)}/100)")

        # Step 3: Compose and send email digest via SMTP
        print(f"\n[3/4] Compiling and dispatching SMTP digest ({len(qualified)} qualified)...")
        email_fn = self.tools.get("send_smtp_email")
        if email_fn and qualified:
            from config import Config
            cards_html = ""
            for q in qualified:
                cards_html += f"""
                <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 18px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <h3 style="margin: 0 0 6px 0; color: #0f172a; font-size: 17px;">{q['title']}</h3>
                            <p style="margin: 0; color: #64748b; font-size: 14px;"><strong>Company:</strong> {q['company']} | <strong>Rate:</strong> {q.get('rate', 'N/A')} | <strong>Platform:</strong> {q.get('platform', 'Web')}</p>
                        </div>
                        <span style="background: #dcfce7; color: #15803d; font-weight: 600; padding: 4px 10px; border-radius: 9999px; font-size: 13px;">
                            Score: {q['match_score']}%
                        </span>
                    </div>
                    <div style="margin-top: 12px; background: #f8fafc; padding: 12px; border-left: 3px solid #3b82f6; border-radius: 4px;">
                        <p style="margin: 0; font-size: 13px; color: #334155; font-style: italic;">
                            "{q['pitch'][:300]}..."
                        </p>
                    </div>
                    <div style="margin-top: 14px;">
                        <a href="{q.get('url', '#')}" style="display: inline-block; background: #2563eb; color: #ffffff; text-decoration: none; padding: 8px 16px; border-radius: 6px; font-size: 13px; font-weight: 500;">
                            Inspect Opportunity via Browser &rarr;
                        </a>
                    </div>
                </div>
                """

            digest_html = f"""
            <!DOCTYPE html>
            <html>
            <head><meta charset="utf-8"></head>
            <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f1f5f9; padding: 24px; margin: 0;">
                <div style="max-width: 680px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; border: 1px solid #cbd5e1;">
                    <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); color: #ffffff; padding: 24px;">
                        <h1 style="margin: 0; font-size: 20px; font-weight: 700;">Ahmad Faraz — Job Intelligence Briefing</h1>
                        <p style="margin: 6px 0 0; color: #94a3b8; font-size: 13px;">Curated remote opportunities & customized CV pitches</p>
                    </div>
                    <div style="padding: 24px;">
                        <div style="display: flex; gap: 12px; margin-bottom: 24px;">
                            <div style="flex: 1; background: #eff6ff; padding: 12px; border-radius: 8px; text-align: center;">
                                <span style="font-size: 22px; font-weight: 700; color: #1d4ed8;">{len(discovered_jobs)}</span>
                                <div style="font-size: 12px; color: #60a5fa; text-transform: uppercase;">Discovered</div>
                            </div>
                            <div style="flex: 1; background: #ecfdf5; padding: 12px; border-radius: 8px; text-align: center;">
                                <span style="font-size: 22px; font-weight: 700; color: #047857;">{len(qualified)}</span>
                                <div style="font-size: 12px; color: #34d399; text-transform: uppercase;">Qualified</div>
                            </div>
                        </div>
                        {cards_html}
                        <div style="margin-top: 24px; padding-top: 14px; border-top: 1px solid #e2e8f0; font-size: 13px; color: #64748b;">
                            <p style="margin: 0; font-weight: 600; color: #334155;">Ahmad Faraz | Software Engineer</p>
                            <p style="margin: 2px 0 0 0;">Sargodha, Pakistan</p>
                            <p style="margin: 2px 0 0 0;"><a href="https://www.linkedin.com/in/ahmad-faraz-/" style="color: #0284c7;">LinkedIn</a> &bull; <a href="https://github.com/ahmadfaraz2" style="color: #0284c7;">GitHub</a></p>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """

            recipient = Config.ALERT_RECIPIENT_EMAIL or "user@example.com"
            res = email_fn(
                to_email=recipient,
                subject=f"🎯 [{len(qualified)} High-Value Matches] Antigravity Job Digest",
                body_html=digest_html,
                body_text=f"Antigravity Job Digest: {len(qualified)} qualified opportunities discovered."
            )
            print(f"      SMTP Status: {res}")

        print("\n[4/4] Autonomous workflow completed successfully.")
        print("=" * 65 + "\n")
        return {"status": "SUCCESS", "processed": len(discovered_jobs), "qualified": len(qualified)}
