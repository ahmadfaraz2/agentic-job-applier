"""
Antigravity Discord Interactive Assistant & Application Dispatcher for Ahmad Faraz.
Enables Ahmad to paste raw LinkedIn job posts, hiring announcements, or URLs directly in Discord DMs,
upload mobile screenshots for automatic native OCR, interact via native Slash (/) and Prefix (!) commands,
and dispatch organic application emails with Ahmad_Faraz_CV.pdf attached.
"""

from __future__ import annotations

import asyncio
import io
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

import discord
from discord import app_commands
from discord.ext import commands

from config import Config
from tools.excel_tracker_tool import get_excel_stats, get_recent_applications, is_already_applied
from tools.post_parser_tool import parse_raw_job_post, strip_all_emojis
from tools.pitch_customizer_tool import generate_tailored_pitch
from tools.email_tool import send_cv_application_email, get_cv_path
from tools.inbox_listener_tool import check_inbound_recruiter_replies
from tools.browser_tool import extract_job_and_email_from_url
from tools.ocr_tool import extract_text_from_image_bytes
from tools.live_job_crawler import fetch_live_job_leads
from tools.followup_tool import get_pending_followups, send_followup_bump, generate_portal_application_kit
from tools.recruiter_hunter_tool import hunt_recruiter_email

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("AntigravityDiscordBot")

# Intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.dm_messages = True

class AntigravityBot(commands.Bot):
    """Custom Bot with automated guild and global slash command synchronization."""

    async def setup_hook(self):
        try:
            guild_id = getattr(Config, "DISCORD_GUILD_ID", None)
            if guild_id:
                guild_obj = discord.Object(id=int(guild_id))
                self.tree.copy_global_to(guild=guild_obj)
                synced = await self.tree.sync(guild=guild_obj)
                logger.info(f"Successfully synced {len(synced)} slash command(s) directly to server 'My Custom Job Applier' (ID: {guild_id}).")
            synced_global = await self.tree.sync()
            logger.info(f"Successfully synced {len(synced_global)} application slash command(s) with Discord globally.")
        except Exception as e:
            logger.error(f"Failed to sync slash commands with Discord: {e}", exc_info=True)

bot = AntigravityBot(command_prefix="!", intents=intents, help_command=None)

# ---------------------------------------------------------------------------
# Security, Server Boundary & Permissions Verification
# ---------------------------------------------------------------------------

def is_authorized_user(user: discord.User | discord.Member) -> bool:
    """Verifies that the user is the owner (Ahmad Faraz) if DISCORD_OWNER_ID is set."""
    if not Config.DISCORD_OWNER_ID:
        return True
    return str(user.id) == str(Config.DISCORD_OWNER_ID).strip()

def is_target_server(guild: Optional[discord.Guild]) -> bool:
    """Strictly ensures all operations occur inside 'My Custom Job Applier' server (never DMs)."""
    if guild is None:
        return False
    target_name = (getattr(Config, "DISCORD_GUILD_NAME", "") or "My Custom Job Applier").strip().lower()
    if guild.name.strip().lower() == target_name:
        return True
    target_id = getattr(Config, "DISCORD_GUILD_ID", None)
    if target_id and guild.id == int(target_id):
        return True
    return False

def get_target_guild_channel(bot_instance: commands.Bot) -> Optional[discord.TextChannel]:
    """Finds the primary text channel inside 'My Custom Job Applier'."""
    for guild in bot_instance.guilds:
        if is_target_server(guild):
            for ch in guild.text_channels:
                if ch.name.lower() == "general" and ch.permissions_for(guild.me).send_messages:
                    return ch
            for ch in guild.text_channels:
                if ch.permissions_for(guild.me).send_messages:
                    return ch
    return None

async def check_interaction_auth(interaction: discord.Interaction) -> bool:
    """Checks slash command server boundary and owner permission."""
    if not is_target_server(interaction.guild):
        await interaction.response.send_message(
            "⛔ **Restricted:** This bot only sends and receives messages inside the **My Custom Job Applier** server.",
            ephemeral=True
        )
        return False

    if not is_authorized_user(interaction.user):
        await interaction.response.send_message(
            "⛔ **Unauthorized:** This bot is exclusively configured for Ahmad Faraz.",
            ephemeral=True
        )
        return False
    return True

# ---------------------------------------------------------------------------
# Interactive Discord UI View (Buttons for Application Dispatch)
# ---------------------------------------------------------------------------

class JobApplicationView(discord.ui.View):
    """Interactive preview view with [🚀 Send Application Email] and [❌ Cancel] buttons."""

    def __init__(
        self,
        parsed_data: Dict[str, Any],
        raw_post: str,
        author_id: int,
        timeout: Optional[float] = 86400.0  # 24 hours
    ):
        super().__init__(timeout=timeout)
        self.parsed_data = parsed_data
        self.raw_post = raw_post
        self.author_id = author_id
        self.message: Optional[discord.Message] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not is_target_server(interaction.guild):
            await interaction.response.send_message(
                "⛔ This button can only be clicked inside the **My Custom Job Applier** server.",
                ephemeral=True
            )
            return False
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "⛔ You are not authorized to interact with this application preview.",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Send Application Email", style=discord.ButtonStyle.success, emoji="🚀")
    async def send_email_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if not interaction.response.is_done():
                await interaction.response.defer()
        except Exception as e_def:
            logger.warning(f"Error deferring interaction response: {e_def}")

        # Disable all buttons immediately to prevent duplicate sends
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

        to_email = self.parsed_data.get("recruiter_email", "")
        company = self.parsed_data.get("company", "")
        job_title = self.parsed_data.get("job_title", "")
        subject_line = self.parsed_data.get("subject_line", "")
        pitch = self.parsed_data.get("tailored_pitch", "")
        location = self.parsed_data.get("location", "")

        # Dispatch application email in background executor
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: send_cv_application_email(
                to_email=to_email,
                job_title=job_title,
                company=company,
                custom_paragraph=pitch,
                job_description=self.raw_post,
                source_platform="LinkedIn / Discord",
                force=True,  # force=True because user explicitly clicked confirm
                custom_subject=subject_line,
                location=location
            )
        )

        if "Success" in result:
            embed = discord.Embed(
                title="✅ Application Email Dispatched Successfully!",
                description=(
                    f"Cold outreach email successfully sent to **{company}** with **`Ahmad_Faraz_CV.pdf`** attached.\n"
                    f"Application details have been recorded into your Excel tracking system."
                ),
                color=0x22C55E,
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="🏢 Company", value=company, inline=True)
            embed.add_field(name="💼 Role", value=job_title, inline=True)
            embed.add_field(name="📩 Sent To", value=to_email, inline=False)
            embed.add_field(name="📝 Subject", value=f"`{subject_line}`", inline=False)
            embed.add_field(name="📎 Attached CV", value="`Ahmad_Faraz_CV.pdf`", inline=True)
            embed.add_field(name="📊 Tracker", value="`applied_jobs_tracker.xlsx`", inline=True)
            embed.set_footer(text="Ahmad Faraz Job Outreach Engine • Google Antigravity")

            edited = False
            try:
                await interaction.edit_original_response(embed=embed, view=self)
                edited = True
            except Exception as e_resp:
                logger.warning(f"Could not edit original response via interaction token: {e_resp}")

            if not edited and self.message:
                try:
                    await self.message.edit(embed=embed, view=self)
                    edited = True
                except Exception as e_msg:
                    logger.warning(f"Could not edit message directly: {e_msg}")

            # CRITICAL GUARANTEE: Always post an explicit delivery confirmation message to the channel!
            try:
                await interaction.channel.send(
                    f"🚀 **Email Dispatched Successfully!**\n"
                    f"Cold outreach email for **{job_title}** has been sent to **{company}** (`{to_email}`) with `Ahmad_Faraz_CV.pdf` attached!\n"
                    f"📁 Tracked in `data/applied_jobs_tracker.xlsx` (Confirmed in your Gmail Sent Mail & Inbox)."
                )
            except Exception as e_send:
                logger.error(f"Failed to post delivery confirmation to channel: {e_send}")
        else:
            # Re-enable button on failure so user can retry immediately!
            for child in self.children:
                if isinstance(child, discord.ui.Button):
                    child.disabled = False

            fail_embed = discord.Embed(
                title="⚠️ Application Dispatch Glitch (Retry Available)",
                description=(
                    f"Encountered an issue dispatching email to **{company}**:\n```\n{result}\n```\n"
                    f"💡 **Button re-enabled:** Click **`[🚀 Send Application Email]`** again to retry."
                ),
                color=0xEF4444,
                timestamp=datetime.now(timezone.utc)
            )
            try:
                await interaction.edit_original_response(embed=fail_embed, view=self)
            except Exception:
                if self.message:
                    try:
                        await self.message.edit(embed=fail_embed, view=self)
                    except Exception:
                        pass
            try:
                await interaction.channel.send(f"⚠️ **Application failed for {company}:** `{result}`. You can click the button on the card above to retry.")
            except Exception:
                pass

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if not interaction.response.is_done():
                await interaction.response.defer()
        except Exception:
            pass

        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

        cancel_embed = discord.Embed(
            title="❌ Application Cancelled",
            description=(
                f"Application for **{self.parsed_data.get('job_title', 'Role')}** at "
                f"**{self.parsed_data.get('company', 'Company')}** was cancelled.\n"
                f"No email was sent and no records were modified."
            ),
            color=0x64748B,
            timestamp=datetime.now(timezone.utc)
        )
        try:
            await interaction.edit_original_response(embed=cancel_embed, view=self)
        except Exception:
            if self.message:
                try:
                    await self.message.edit(embed=cancel_embed, view=self)
                except Exception:
                    pass
        try:
            await interaction.channel.send(f"❌ Application for **{self.parsed_data.get('company', 'Company')}** was cancelled.")
        except Exception:
            pass

    async def on_timeout(self):
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        if self.message:
            try:
                timeout_embed = discord.Embed(
                    title="⏱️ Application Confirmation Timed Out",
                    description=(
                        f"Interaction timed out for **{self.parsed_data.get('job_title', 'Role')}** at "
                        f"**{self.parsed_data.get('company', 'Company')}** (15m limit). Buttons disabled."
                    ),
                    color=0x94A3B8
                )
                await self.message.edit(embed=timeout_embed, view=self)
            except Exception:
                pass

class FollowUpBumpView(discord.ui.View):
    """Interactive card for sending 1-click follow-up bump emails for applications >= 4 days old."""

    def __init__(
        self,
        record: Dict[str, Any],
        author_id: int,
        timeout: Optional[float] = 86400.0  # 24 hours
    ):
        super().__init__(timeout=timeout)
        self.record = record
        self.author_id = author_id
        self.message: Optional[discord.Message] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not is_target_server(interaction.guild):
            await interaction.response.send_message(
                "⛔ This button can only be clicked inside the **My Custom Job Applier** server.",
                ephemeral=True
            )
            return False
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "⛔ You are not authorized to interact with this follow-up card.",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Send Follow-Up Bump", style=discord.ButtonStyle.primary, emoji="🚀")
    async def bump_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if not interaction.response.is_done():
                await interaction.response.defer()
        except Exception as e_def:
            logger.warning(f"Error deferring follow-up interaction: {e_def}")

        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

        loop = asyncio.get_running_loop()
        res = await loop.run_in_executor(None, send_followup_bump, self.record)

        if "Success" in res:
            embed = discord.Embed(
                title="✅ Follow-Up Bump Dispatched Successfully!",
                description=(
                    f"Polite follow-up email sent to **{self.record.get('company')}** (`{self.record.get('recipient_email')}`) "
                    f"with `Ahmad_Faraz_CV.pdf` re-attached.\n"
                    f"Application status updated to `FOLLOWED_UP` in your Excel tracker."
                ),
                color=0x22C55E,
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="🏢 Company", value=self.record.get("company", ""), inline=True)
            embed.add_field(name="💼 Role", value=self.record.get("job_title", ""), inline=True)
            embed.add_field(name="🕒 Prior Application", value=f"{self.record.get('days_ago', 0)} days ago ({self.record.get('timestamp', '')})", inline=False)
            embed.set_footer(text="Ahmad Faraz Job Outreach Engine • Zero-Emoji Policy Enforced")

            try:
                await interaction.edit_original_response(embed=embed, view=self)
            except Exception:
                if self.message:
                    try:
                        await self.message.edit(embed=embed, view=self)
                    except Exception:
                        pass

            try:
                await interaction.channel.send(
                    f"🚀 **Follow-Up Dispatched!** Follow-up email sent to **{self.record.get('company')}** (`{self.record.get('recipient_email')}`)."
                )
            except Exception:
                pass
        else:
            for child in self.children:
                if isinstance(child, discord.ui.Button):
                    child.disabled = False

            fail_embed = discord.Embed(
                title="⚠️ Follow-Up Dispatch Glitch (Retry Available)",
                description=f"Could not send follow-up to **{self.record.get('company')}**:\n```\n{res}\n```\nClick the button above to retry.",
                color=0xEF4444,
                timestamp=datetime.now(timezone.utc)
            )
            try:
                await interaction.edit_original_response(embed=fail_embed, view=self)
            except Exception:
                if self.message:
                    try:
                        await self.message.edit(embed=fail_embed, view=self)
                    except Exception:
                        pass

    async def on_timeout(self):
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        if self.message:
            try:
                timeout_embed = discord.Embed(
                    title="⏱️ Follow-Up Card Timed Out",
                    description=f"Follow-up interaction for **{self.record.get('company')}** timed out. Buttons disabled.",
                    color=0x94A3B8
                )
                await self.message.edit(embed=timeout_embed, view=self)
            except Exception:
                pass

# ---------------------------------------------------------------------------
# Shared Embed Builders
# ---------------------------------------------------------------------------

def build_stats_embed(stats: Dict[str, Any]) -> discord.Embed:
    total_apps = stats.get("total_applications", 0)
    interviews = stats.get("interview_invites", 0)
    unique_comps = stats.get("unique_companies", 0)
    companies_list = stats.get("companies", [])

    embed = discord.Embed(
        title="📊 Excel Application Tracker Summary",
        color=0x22C55E,
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(name="📬 Total Applications Sent", value=f"**{total_apps}**", inline=True)
    embed.add_field(name="🎉 Interview Invites", value=f"**{interviews}**", inline=True)
    embed.add_field(name="🏢 Unique Companies", value=f"**{unique_comps}**", inline=True)

    if companies_list:
        recent_display = "\n".join([f"• {c}" for c in companies_list[-12:]])
        embed.add_field(name="Applied Companies (Recent)", value=recent_display, inline=False)

    embed.add_field(
        name="📁 Tracker File",
        value="`data/applied_jobs_tracker.xlsx`",
        inline=False
    )
    embed.set_footer(text="Ahmad Faraz Job Outreach Engine")
    return embed

def build_check_embed(replies: List[Dict[str, Any]]) -> discord.Embed:
    if not replies:
        return discord.Embed(
            title="📬 Inbound Recruiter Check",
            description="No new replies or interview invitations detected from applied companies at this time.",
            color=0x64748B,
            timestamp=datetime.now(timezone.utc)
        )

    embed = discord.Embed(
        title=f"🎉 Detected {len(replies)} Recruiter Response(s)!",
        color=0x10B981,
        timestamp=datetime.now(timezone.utc)
    )
    for r in replies[:5]:
        embed.add_field(
            name=f"🏢 {r.get('company')} — [{r.get('classification', 'REPLY')}]",
            value=(
                f"**From:** `{r.get('sender', '')}`\n"
                f"**Subject:** {r.get('subject', '')}\n"
                f"**Snippet:** {r.get('snippet', '')[:160]}..."
            ),
            inline=False
        )
    embed.set_footer(text="Excel tracker updated automatically with response status.")
    return embed

def build_history_embed(records: List[Dict[str, Any]]) -> discord.Embed:
    if not records:
        return discord.Embed(
            title="📜 Recent Application History",
            description="No application history found in `applied_jobs_tracker.xlsx`.",
            color=0x64748B,
            timestamp=datetime.now(timezone.utc)
        )

    embed = discord.Embed(
        title="📜 Recent Application History (Last 5)",
        color=0x3B82F6,
        timestamp=datetime.now(timezone.utc)
    )
    for rec in records:
        embed.add_field(
            name=f"{rec.get('id')} • {rec.get('company')} — {rec.get('job_title')}",
            value=(
                f"**To:** `{rec.get('recipient_email')}`\n"
                f"**Subject:** {rec.get('subject')}\n"
                f"**Time:** {rec.get('timestamp')} • **Status:** `{rec.get('status')}`"
            ),
            inline=False
        )
    embed.set_footer(text="Maintained in data/applied_jobs_tracker.xlsx")
    return embed

def build_help_embed(user_id: int) -> discord.Embed:
    embed = discord.Embed(
        title="🚀 Ahmad Faraz — Antigravity Job Outreach Bot Guide",
        description=(
            "Welcome! This bot automates your job application workflow directly from Discord.\n\n"
            "### 📥 3 Easy Ways to Apply:\n"
            "1. 📸 **Mobile Screenshot:** Upload any screenshot of a LinkedIn job post from your phone! Native OCR extracts the text instantly.\n"
            "2. 📝 **Drop Raw Text or Link:** Paste unformatted hiring announcements, LinkedIn posts, or URLs directly into this chat.\n"
            "3. ⚡ **Slash Command:** Type `/apply` to provide post text or upload a screenshot with auto-complete!\n\n"
            "### ⚡ What Happens Next:\n"
            "• **Contextual AI Intelligence:** Extracts Company, Role, Recruiter Email, and exact Subject requirements.\n"
            "• **Domain Intelligence Hunter:** Auto-resolves recruiter emails for top tech employers even when missing in post.\n"
            "• **Interactive Preview:** The bot formats an embed with all parsed information.\n"
            "• **1-Click Dispatch:** Click **`[🚀 Send Application Email]`** to send your cold email with `Ahmad_Faraz_CV.pdf` attached.\n\n"
            "### 🛠️ Slash (/) & Prefix (!) Commands:\n"
            "• `/scan` (or `!scan`) — Crawl live feeds (LinkedIn Pakistan, Remotive, Curated) and send 1-click approval cards.\n"
            "• `/followup` (or `!followup`) — Review applications pending >= 4 days and send 1-click follow-up bump emails.\n"
            "• `/portal` (or `!portal`) — Generate copy-paste answers for ATS/NAVTTC NSIS web portal forms.\n"
            "• `/apply` (or paste post) — Apply to a job post, link, or screenshot.\n"
            "• `/stats` (or `!stats`) — View total applications, interview invites, and unique companies from Excel.\n"
            "• `/check` (or `!check`) — Scan your Gmail inbox for recruiter replies and interview invitations.\n"
            "• `/history` (or `!history`) — View your last 5 dispatched applications.\n"
            "• `/help` (or `!help`) — Display this guidance message."
        ),
        color=0x6366F1
    )
    if not Config.DISCORD_OWNER_ID:
        embed.set_footer(text=f"Your Discord User ID is: {user_id} (Add DISCORD_OWNER_ID in .env to lock bot)")
    else:
        embed.set_footer(text="Secured & Locked to Ahmad Faraz • Zero-Emoji Policy Enforced")
    return embed

def build_diagnostics_embed() -> discord.Embed:
    cv_file = get_cv_path()
    cv_ok = cv_file is not None and cv_file.exists()
    cv_size_kb = round(cv_file.stat().st_size / 1024, 1) if cv_ok else 0

    stats = get_excel_stats()
    total_apps = stats.get("total_applications", 0)
    interview_invites = stats.get("interview_invites", 0)
    unique_comps = stats.get("unique_companies", 0)

    recent = get_recent_applications(1)
    last_app_str = "None yet"
    if recent:
        last = recent[0]
        last_app_str = f"**{last.get('id', '')}** to **{last.get('company', '')}** (`{last.get('recipient_email', '')}`)\n🕒 {last.get('timestamp', '')} • Status: `{last.get('status', 'APPLIED')}`"

    embed = discord.Embed(
        title="🟢 Antigravity Outreach Engine Health & Diagnostics",
        description="All engine subsystems are fully operational and ready to dispatch applications.",
        color=0x22C55E,
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(
        name="📧 Gmail SMTP",
        value=f"🟢 **Connected** (`{Config.SMTP_USER}`)\nHost: `{Config.SMTP_HOST}:{Config.SMTP_PORT}`",
        inline=True
    )
    embed.add_field(
        name="📎 CV Document",
        value=f"🟢 **Found** (`{cv_file.name if cv_ok else 'Missing'}` ~{cv_size_kb} KB)" if cv_ok else "🔴 **Missing**",
        inline=True
    )
    embed.add_field(
        name="📊 Excel Tracker",
        value=f"🟢 **{total_apps} Sent** | **{unique_comps} Companies**",
        inline=True
    )
    embed.add_field(
        name="🕒 Most Recent Dispatched Email",
        value=last_app_str,
        inline=False
    )
    embed.add_field(
        name="🛡️ Zero-Emoji Mandate",
        value="🟢 **Active** (All outbound emails 100% clean)",
        inline=True
    )
    embed.add_field(
        name="🤖 AI Model",
        value="🟢 **Gemini 3.8 Flash** via Antigravity SDK",
        inline=True
    )
    embed.set_footer(text="Ahmad Faraz Job Outreach Engine • Google Antigravity")
    return embed

def build_portal_kit_embed(kit: Dict[str, str], raw_url: str = "") -> discord.Embed:
    company = kit.get("company", "Company")
    job_title = kit.get("job_title", "Software Engineer")
    portal_name = kit.get("portal_name", "Online Portal")

    embed = discord.Embed(
        title=f"📋 Portal Application Kit: {company} ({portal_name})",
        description=(
            f"This opening requires direct online portal submission via **{portal_name}**.\n"
            f"Here are humanized, tailored application answers ready to copy-paste into the form:"
        ),
        color=0x8B5CF6,
        timestamp=datetime.now(timezone.utc)
    )
    if raw_url:
        embed.add_field(name="🌐 Application Link", value=f"[Open Application Portal]({raw_url})", inline=False)
    embed.add_field(name="🏢 Company", value=company, inline=True)
    embed.add_field(name="💼 Role / Title", value=job_title, inline=True)
    embed.add_field(name="📝 'About You / Professional Summary' (Copy-Paste)", value=f"```{kit.get('about_me', '')}```", inline=False)
    embed.add_field(name="💡 'Why Are You a Good Fit for Us?' (Copy-Paste)", value=f"```{kit.get('why_company', '')}```", inline=False)
    embed.add_field(name="📄 Cover Note / Message to Recruiter", value=f"```{kit.get('cover_note', '')[:900]}...```", inline=False)
    embed.set_footer(text="Zero-Emoji Outreach Mandate Enforced • Attach Ahmad_Faraz_CV.pdf when submitting")
    return embed

def build_application_preview(parsed: Dict[str, Any], is_dup: bool) -> discord.Embed:
    company = parsed.get("company", "")
    job_title = parsed.get("job_title", "")
    to_email = parsed.get("recruiter_email", "")
    location = parsed.get("location", "") or "On-site / Remote"
    subject_line = parsed.get("subject_line", "")
    tailored_pitch = parsed.get("tailored_pitch", "")
    model_engine = parsed.get("model_engine", "Contextual AI & Domain Reasoning Engine")
    email_method = parsed.get("email_resolution_method", "DIRECT")

    pitch_preview = tailored_pitch
    if len(pitch_preview) > 900:
        pitch_preview = pitch_preview[:900] + "..."

    embed_color = 0xF59E0B if is_dup else 0x3B82F6
    embed = discord.Embed(
        title=f"📋 Job Application Preview: {company}",
        description="Antigravity analyzed the job post and formulated your tailored application.",
        color=embed_color,
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(name="🏢 Company", value=company, inline=True)
    embed.add_field(name="💼 Role / Title", value=job_title, inline=True)
    embed.add_field(name="📍 Location", value=location, inline=True)

    email_display = f"`{to_email}`"
    if email_method in ("VERIFIED_MAP", "DNS_MX_DISCOVERY"):
        email_display += " *(Auto-Resolved via Verified Tech Directory)*"
    elif email_method and email_method not in ("DIRECT", "Live Scanner"):
        email_display += f" *({email_method})*"

    embed.add_field(name="📩 Recruiter Email", value=email_display, inline=False)
    embed.add_field(name="📝 Subject Line", value=f"`{subject_line}`", inline=False)

    if is_dup:
        embed.add_field(
            name="🛡️ Deduplication Shield",
            value="⚠️ **Warning: You have already applied to this company/email in your tracker!**\n"
                  "*(Clicking Send will override and send again)*",
            inline=False
        )
    else:
        embed.add_field(
            name="🛡️ Deduplication Shield",
            value="🟢 **Fresh Opening** — Not present in your application tracker.",
            inline=False
        )

    embed.add_field(name="📄 Attachment", value="`Ahmad_Faraz_CV.pdf`", inline=True)
    embed.add_field(name="🤖 Intelligence Engine", value=model_engine, inline=True)
    embed.add_field(name="💬 Dynamic Tailored Pitch Preview", value=f"```{pitch_preview}```", inline=False)
    embed.set_footer(text="Zero-Emoji Outreach Mandate Enforced • Click below to dispatch")
    return embed

# ---------------------------------------------------------------------------
# Live Job Leads Scanner & Dispatcher
# ---------------------------------------------------------------------------

async def scan_and_send_leads(target_destination, author_id: int) -> int:
    """Scans live multi-source job feeds (LinkedIn Pakistan, Remotive API, Curated pipeline), checks deduplication against Excel, and dispatches interactive cards."""
    sent_count = 0
    loop = asyncio.get_running_loop()

    # Discover live job leads dynamically across all active sources
    leads = await loop.run_in_executor(None, lambda: fetch_live_job_leads(limit=8))

    for lead in leads:
        company = lead["company"]
        email = lead.get("email", "").strip()
        title = lead["title"]
        raw_post = lead["post"]
        is_portal = lead.get("is_portal", False)
        portal_url = lead.get("url", "")
        portal_name = lead.get("portal_name", "Online Portal")

        # Portal-only opening without an email
        if is_portal and not email:
            kit = await loop.run_in_executor(
                None,
                lambda: generate_portal_application_kit(company, title, raw_post, portal_name or "Portal")
            )
            embed = build_portal_kit_embed(kit, raw_url=portal_url)
            await target_destination.send(embed=embed)
            sent_count += 1
            await asyncio.sleep(0.5)
            continue

        if not email:
            continue

        # Check deduplication against Excel tracker
        is_dup = await loop.run_in_executor(None, is_already_applied, email, company, title)
        if is_dup:
            logger.info(f"[Live Scanner] Skipping already applied opening: {company} ({email})")
            continue

        try:
            pitch = await loop.run_in_executor(
                None,
                generate_tailored_pitch,
                title,
                company,
                raw_post
            )
            parsed = {
                "company": company,
                "job_title": title,
                "recruiter_email": email,
                "location": lead.get("location", "Lahore / Remote"),
                "subject_line": f"Application for {title} - Ahmad Faraz",
                "tailored_pitch": pitch,
                "model_engine": "Contextual AI & Domain Reasoning Engine",
                "email_resolution_method": lead.get("source", "Live Scanner")
            }

            embed = build_application_preview(parsed, is_dup=False)
            view = JobApplicationView(
                parsed_data=parsed,
                raw_post=raw_post,
                author_id=author_id,
                timeout=86400.0  # 24 hours
            )

            sent_msg = await target_destination.send(embed=embed, view=view)
            view.message = sent_msg
            sent_count += 1
            await asyncio.sleep(0.5)  # Gentle Discord rate limit pacing
        except Exception as e_lead:
            logger.error(f"[Live Scanner] Error dispatching card for {company}: {e_lead}")

    return sent_count

# ---------------------------------------------------------------------------
# Bot Events
# ---------------------------------------------------------------------------

@bot.event
async def on_ready():
    logger.info(f"Antigravity Discord Bot logged in as: {bot.user} (ID: {bot.user.id})")
    print("\n" + "=" * 65)
    print(f"  🤖 ANTIGRAVITY DISCORD OUTREACH BOT IS ONLINE!")
    print(f"  • Bot Account:  {bot.user}")
    print(f"  • Connected:    {len(bot.guilds)} server(s)")
    print(f"  • Bound Server: My Custom Job Applier (DMs Strictly Disabled)")
    if Config.DISCORD_OWNER_ID:
        print(f"  • Owner Lock:   Authorized User ID: {Config.DISCORD_OWNER_ID}")
    print("=" * 65 + "\n")
    activity = discord.Activity(type=discord.ActivityType.watching, name="My Custom Job Applier 💼")
    await bot.change_presence(activity=activity)

    # Automatically dispatch newly discovered job leads to 'My Custom Job Applier' server channel on startup
    if not getattr(bot, "_has_dispatched_initial_leads", False):
        bot._has_dispatched_initial_leads = True
        try:
            channel = get_target_guild_channel(bot)
            if channel:
                logger.info(f"Scanning and dispatching live job leads to #{channel.name} in '{channel.guild.name}'...")
                intro_embed = discord.Embed(
                    title="🔍 Fresh Job Openings Ready for Your Approval",
                    description=(
                        "I scanned active tech job listings in Lahore / Pakistan matching your profile.\n"
                        "Below are the verified unapplied opportunities. Review the details and click "
                        "**`[🚀 Send Application Email]`** on any card to dispatch with your CV attached!"
                    ),
                    color=0x22C55E,
                    timestamp=datetime.now(timezone.utc)
                )
                await channel.send(embed=intro_embed)
                owner_id = int(Config.DISCORD_OWNER_ID) if Config.DISCORD_OWNER_ID else bot.user.id
                count = await scan_and_send_leads(channel, author_id=owner_id)
                logger.info(f"Successfully delivered {count} lead cards to #{channel.name} in '{channel.guild.name}'.")
            else:
                logger.warning("Target server 'My Custom Job Applier' channel not found for initial lead dispatch.")
        except Exception as e:
            logger.error(f"Failed to dispatch initial job leads to server: {e}", exc_info=True)

@bot.event
async def on_message(message: discord.Message):
    # Ignore messages from bots (including self)
    if message.author.bot:
        return

    # Strictly enforce: ONLY receive and send messages in 'My Custom Job Applier' server (NEVER in DMs)
    if not is_target_server(message.guild):
        logger.debug(f"Ignoring non-server or DM message from {message.author} per server-only policy.")
        return

    logger.info(
        f"Incoming server message from {message.author} (ID: {message.author.id}) in #{message.channel.name} "
        f"({message.guild.name}): content='{message.content[:60]}', attachments={len(message.attachments)}"
    )

    # Check authorization (only Ahmad Faraz)
    if not is_authorized_user(message.author):
        logger.warning(f"Blocked unauthorized message from {message.author} (ID: {message.author.id}) in {message.guild.name}")
        return

    # Process standard prefix commands first (e.g. !stats, !check, !history, !help, !scan)
    if message.content.strip().startswith("!"):
        await bot.process_commands(message)
        return

    raw_text = message.content.strip()
    if bot.user in message.mentions:
        raw_text = message.content.replace(f"<@{bot.user.id}>", "").strip()
    clean_lower = raw_text.lower().strip()

    # Detect screenshot or image attachments
    has_image = bool(
        message.attachments and any(
            (att.content_type and att.content_type.startswith("image/")) or
            any(att.filename.lower().endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp"))
            for att in message.attachments
        )
    )

    # If NO image is attached, inspect natural language conversational intents
    if not has_image and raw_text and "@" not in raw_text:
        # Intent 1: Search / Find / Scan for Jobs
        SEARCH_TRIGGERS = [
            "search", "scan", "find job", "find jobs", "more job", "more jobs",
            "available job", "available jobs", "give me job", "give me jobs",
            "5 to 7", "new jobs", "show jobs", "get jobs", "any job"
        ]
        if any(trig in clean_lower for trig in SEARCH_TRIGGERS):
            status_msg = await message.channel.send("🔍 **Scanning active software & tech job openings matching your profile...**")
            async with message.channel.typing():
                count = await scan_and_send_leads(message.channel, message.author.id)
                if count == 0:
                    await status_msg.edit(content="✅ **All currently scanned opportunities have already been applied to!**\nNo duplicate emails will be dispatched. I will alert you as soon as new positions appear.")
                else:
                    await status_msg.edit(content=f"📬 **Delivered {count} fresh job approval cards below!** Review the details on each card and click **`[🚀 Send Application Email]`** to dispatch with your CV attached.")
            return

        # Intent 2: Engine Diagnostics & Status ("is it working", "any issue", "status")
        STATUS_TRIGGERS = [
            "is it working", "is it running", "any issue", "is something break",
            "is anything break", "is it broken", "status", "health", "check bot",
            "diagnostics", "ping", "are you working", "how is it going"
        ]
        if any(trig in clean_lower for trig in STATUS_TRIGGERS):
            async with message.channel.typing():
                diag_embed = build_diagnostics_embed()
                await message.channel.send(embed=diag_embed)
            return

        # Intent 3: Check Recruiter Replies / Inbox
        REPLY_TRIGGERS = [
            "check reply", "check replies", "any reply", "any replies",
            "inbox", "recruiter reply", "interviews", "check email", "check mail"
        ]
        if any(trig in clean_lower for trig in REPLY_TRIGGERS):
            status_msg = await message.channel.send("📬 **Scanning your Gmail IMAP inbox for recruiter responses...**")
            async with message.channel.typing():
                loop = asyncio.get_running_loop()
                replies = await loop.run_in_executor(
                    None,
                    lambda: check_inbound_recruiter_replies(limit=30, notify_discord=False)
                )
                embed = build_check_embed(replies)
                await status_msg.edit(content=None, embed=embed)
            return

        # Intent 4: Application Stats
        STATS_TRIGGERS = [
            "stats", "how many applied", "application stats", "total applications", "tracker stats"
        ]
        if any(trig == clean_lower or clean_lower.startswith(trig) for trig in STATS_TRIGGERS):
            async with message.channel.typing():
                loop = asyncio.get_running_loop()
                stats = await loop.run_in_executor(None, get_excel_stats)
                embed = build_stats_embed(stats)
                await message.channel.send(embed=embed)
            return

        # Intent 5: Application History
        HISTORY_TRIGGERS = [
            "history", "recent applications", "last applications", "what did i send"
        ]
        if any(trig == clean_lower or clean_lower.startswith(trig) for trig in HISTORY_TRIGGERS):
            async with message.channel.typing():
                loop = asyncio.get_running_loop()
                records = await loop.run_in_executor(None, lambda: get_recent_applications(limit=5))
                embed = build_history_embed(records)
                await message.channel.send(embed=embed)
            return

        # Intent 6: Follow-Up Bump Checker
        FOLLOWUP_TRIGGERS = [
            "followup", "follow up", "follow-up", "bump", "pending followups",
            "pending follow up", "pending follow-ups", "who to follow up"
        ]
        if any(trig in clean_lower for trig in FOLLOWUP_TRIGGERS):
            async with message.channel.typing():
                loop = asyncio.get_running_loop()
                pending = await loop.run_in_executor(None, lambda: get_pending_followups(min_days=4, max_days=14))
                if not pending:
                    embed = discord.Embed(
                        title="📬 Application Follow-Up Status",
                        description=(
                            "🟢 **All applications are up to date!**\n\n"
                            "No applications are currently pending >= 4 days without response.\n"
                            "The engine automatically alerts you when applications reach the 4-day follow-up window."
                        ),
                        color=0x22C55E,
                        timestamp=datetime.now(timezone.utc)
                    )
                    await message.channel.send(embed=embed)
                else:
                    intro_embed = discord.Embed(
                        title=f"📬 Found {len(pending)} Application(s) Awaiting Follow-Up (>= 4 Days)",
                        description="Review the pending applications below. Click **`[🚀 Send Follow-Up Bump]`** to send a polite follow-up with your CV re-attached.",
                        color=0x3B82F6,
                        timestamp=datetime.now(timezone.utc)
                    )
                    await message.channel.send(embed=intro_embed)
                    for rec in pending:
                        embed = discord.Embed(
                            title=f"⏳ Follow-Up Candidate: {rec['company']}",
                            color=0xF59E0B,
                            timestamp=datetime.now(timezone.utc)
                        )
                        embed.add_field(name="🏢 Company", value=rec["company"], inline=True)
                        embed.add_field(name="💼 Role", value=rec["job_title"], inline=True)
                        embed.add_field(name="📩 Recipient", value=f"`{rec['recipient_email']}`", inline=True)
                        embed.add_field(name="🕒 Applied", value=f"**{rec['days_ago']} days ago** ({rec['timestamp']})", inline=True)
                        embed.add_field(name="📝 Original Subject", value=f"`{rec['subject']}`", inline=False)

                        view = FollowUpBumpView(record=rec, author_id=message.author.id)
                        sent_msg = await message.channel.send(embed=embed, view=view)
                        view.message = sent_msg
                        await asyncio.sleep(0.5)
            return

        # Intent 7: Portal / NAVTTC Kit
        PORTAL_TRIGGERS = [
            "portal", "navttc", "nsis", "portal kit", "ats form"
        ]
        if any(trig in clean_lower for trig in PORTAL_TRIGGERS):
            async with message.channel.typing():
                loop = asyncio.get_running_loop()
                portal_name = "NAVTTC NSIS Portal" if any(k in clean_lower for k in ("navttc", "nsis")) else "Web Portal"
                kit = await loop.run_in_executor(
                    None,
                    lambda: generate_portal_application_kit(
                        company="NAVTTC / Partner Organization" if "navttc" in clean_lower else "Target Employer",
                        job_title="Software Engineering Trainee" if "navttc" in clean_lower else "Associate Software Engineer",
                        portal_name=portal_name
                    )
                )
                embed = build_portal_kit_embed(kit)
                await message.channel.send(embed=embed)
            return

        # Intent 8: Help / Guide
        HELP_TRIGGERS = [
            "help", "commands", "guide", "what can you do", "options"
        ]
        if any(trig == clean_lower or clean_lower.startswith(trig) for trig in HELP_TRIGGERS):
            embed = build_help_embed(message.author.id)
            await message.channel.send(embed=embed)
            return

    # In 'My Custom Job Applier', treat messages as job posts, URLs, or OCR images
    message.content = raw_text
    await handle_incoming_job_post(message)

# ---------------------------------------------------------------------------
# Raw Job Post Ingestion & Model Analysis
# ---------------------------------------------------------------------------

async def handle_incoming_job_post(message: discord.Message):
    """Parses raw post text, performs OCR on screenshot attachments, checks duplicates, and prompts with interactive buttons."""
    raw_text = message.content.strip()

    # Detect screenshot or image attachments
    image_attachments = []
    if message.attachments:
        for att in message.attachments:
            if (att.content_type and att.content_type.startswith("image/")) or any(
                att.filename.lower().endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp")
            ):
                image_attachments.append(att)

    if not raw_text and not image_attachments:
        return

    # Filter out casual short chatter that is not a job post
    JOB_KEYWORDS = (
        "hiring", "intern", "developer", "engineer", "opening", "job", "apply", "cv", "resume",
        "position", "stack", "full-time", "part-time", "remotely", "qualification", "candidate"
    )
    is_job_text = any(kw in raw_text.lower() for kw in JOB_KEYWORDS) or len(raw_text) > 80
    if not image_attachments and not is_job_text and not "@" in raw_text and not re.search(r'https?://', raw_text):
        await message.channel.send(
            "👋 **Hi Ahmad!** Paste a complete job post, upload a screenshot, or type `/help` (or `!help`) to see all commands!"
        )
        return

    status_msg = None

    # Visual typing indicator while model thinks
    async with message.channel.typing():
        loop = asyncio.get_running_loop()

        # Handle Screenshot / Image Attachments via Native OCR
        if image_attachments:
            img_count_str = f"{len(image_attachments)} image(s)" if len(image_attachments) > 1 else "image"
            status_msg = await message.reply(f"⏳ **{img_count_str.capitalize()} received! Processing screenshot, please wait a moment...**")

            ocr_texts = []
            for idx, att in enumerate(image_attachments, 1):
                if len(image_attachments) > 1:
                    await status_msg.edit(content=f"⏳ **Processing image {idx} of {len(image_attachments)} via native OCR...**")
                img_bytes = await att.read()
                extracted = await extract_text_from_image_bytes(img_bytes)
                if extracted and extracted.strip():
                    ocr_texts.append(extracted.strip())

            if not ocr_texts:
                await status_msg.edit(
                    content=(
                        "⚠️ **Processing complete, but could not detect readable text in the image.**\n"
                        "Please ensure the screenshot is clear and contains visible text, or paste the post text directly."
                    )
                )
                return

            combined_ocr = "\n\n".join(ocr_texts)
            if raw_text:
                raw_text = f"{raw_text}\n\n{combined_ocr}"
            else:
                raw_text = combined_ocr

            await status_msg.edit(content="🧠 **Text extracted! Formulating application with Gemini 3.8 Flash...**")

        # Check if input is a standalone URL
        url_match = re.match(r'^(https?://[^\s]+)$', raw_text.strip())
        if url_match:
            job_url = url_match.group(1)

            # Check if this is a LinkedIn feed/post link that requires login
            is_linkedin_feed = bool(
                re.search(r'linkedin\.com/(posts|feed/update|pulse)/', job_url, re.IGNORECASE)
                or "lnkd.in/" in job_url
            )
            if is_linkedin_feed:
                feed_embed = discord.Embed(
                    title="🔒 LinkedIn Login Wall Detected",
                    description=(
                        "LinkedIn blocks external automated tools from reading private feed posts via link (`linkedin.com/posts/...`).\n\n"
                        "💡 **The Fast 1-Second Solution on Mobile:**\n"
                        "Simply take a **screenshot** of the post on your phone and **send the picture directly to this chat**!\n\n"
                        "I will read the screenshot instantly via native OCR and formulate your application email with your CV attached."
                    ),
                    color=0x3B82F6
                )
                await message.channel.send(embed=feed_embed)
                return

            await message.channel.send(f"🌐 Browsing job URL: `<{job_url}>`...")
            extracted = await loop.run_in_executor(None, extract_job_and_email_from_url, job_url)
            if extracted.get("status") == "SUCCESS" and extracted.get("summary"):
                raw_text = (
                    f"Job Title: {extracted.get('title', '')}\n"
                    f"Company: {extracted.get('company', '')}\n"
                    f"Source URL: {job_url}\n"
                    f"Emails: {', '.join(extracted.get('emails', []))}\n\n"
                    f"{extracted.get('summary', '')}"
                )

        # Parse with Gemini 3.8 Flash intelligence engine
        parsed = await loop.run_in_executor(None, parse_raw_job_post, raw_text)

        to_email = parsed.get("recruiter_email", "").strip()
        company = parsed.get("company", "").strip()
        job_title = parsed.get("job_title", "").strip()

        if not to_email:
            # Check if an ATS / Portal or application link was detected
            portal_url = parsed.get("portal_url", "")
            is_portal = parsed.get("is_portal", False)
            portal_name = parsed.get("portal_name", "Online Portal")

            urls_in_post = re.findall(r'https?://[^\s]+', raw_text)
            if not portal_url and urls_in_post:
                portal_url = urls_in_post[0]
                is_portal = True

            if is_portal or portal_url:
                kit = await loop.run_in_executor(
                    None,
                    lambda: generate_portal_application_kit(
                        company=company or "Target Company",
                        job_title=job_title or "Software Engineer",
                        job_description=raw_text,
                        portal_name=portal_name or "Portal"
                    )
                )
                portal_embed = build_portal_kit_embed(kit, raw_url=portal_url)
                if status_msg:
                    await status_msg.edit(content="📋 **ATS / Web Portal Detected! Here is your Application Kit:**", embed=portal_embed)
                else:
                    await message.channel.send(embed=portal_embed)
                return

            no_email_embed = discord.Embed(
                title="⚠️ Recruiter Email Not Found",
                description=(
                    f"I parsed the post for **{company}** (`{job_title}`), but could not detect an email address in the text, "
                    f"and this company domain was not found in our verified employer directory.\n\n"
                    f"💡 **How to proceed:**\n"
                    f"• Paste the post again with recruiter email: `Send CV to hr@company.com`\n"
                    f"• Or type `/portal company:{company} role:{job_title}` to get a Portal Application Kit!"
                ),
                color=0xF59E0B
            )
            no_email_embed.add_field(name="🏢 Detected Company", value=company or "Unknown", inline=True)
            no_email_embed.add_field(name="💼 Detected Role", value=job_title or "Unknown", inline=True)
            no_email_embed.set_footer(text=f"Engine: {parsed.get('model_engine', 'Contextual AI')}")

            if status_msg:
                await status_msg.edit(content="⚠️ **Processing complete.** (Could not detect recruiter email)", embed=no_email_embed)
            else:
                await message.channel.send(embed=no_email_embed)
            return

        # Check deduplication against Excel tracker
        is_dup = await loop.run_in_executor(
            None,
            is_already_applied,
            to_email,
            company,
            job_title
        )

        embed = build_application_preview(parsed, is_dup)

        view = JobApplicationView(
            parsed_data=parsed,
            raw_post=raw_text,
            author_id=message.author.id
        )

        if status_msg:
            await status_msg.edit(content="✅ **Done! Here is your application preview:**", embed=embed, view=view)
            view.message = status_msg
        else:
            sent_msg = await message.channel.send(embed=embed, view=view)
            view.message = sent_msg

# ---------------------------------------------------------------------------
# Native Application Slash (/) Commands
# ---------------------------------------------------------------------------

@bot.tree.command(name="help", description="Show the job application assistant guide and available commands")
async def slash_help(interaction: discord.Interaction):
    if not await check_interaction_auth(interaction):
        return
    embed = build_help_embed(interaction.user.id)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="stats", description="View application stats and interview invites from applied_jobs_tracker.xlsx")
async def slash_stats(interaction: discord.Interaction):
    if not await check_interaction_auth(interaction):
        return
    await interaction.response.defer()
    loop = asyncio.get_running_loop()
    stats = await loop.run_in_executor(None, get_excel_stats)
    embed = build_stats_embed(stats)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="check", description="Scan Gmail inbox for recruiter replies and interview invitations")
async def slash_check(interaction: discord.Interaction):
    if not await check_interaction_auth(interaction):
        return
    await interaction.response.defer()
    loop = asyncio.get_running_loop()
    replies = await loop.run_in_executor(
        None,
        lambda: check_inbound_recruiter_replies(limit=30, notify_discord=False)
    )
    embed = build_check_embed(replies)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="history", description="Display your last 5 sent applications")
async def slash_history(interaction: discord.Interaction):
    if not await check_interaction_auth(interaction):
        return
    await interaction.response.defer()
    loop = asyncio.get_running_loop()
    records = await loop.run_in_executor(None, lambda: get_recent_applications(limit=5))
    embed = build_history_embed(records)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="apply", description="Submit a job post text or screenshot to formulate an application email")
@app_commands.describe(
    post="Paste the raw text of the job post or a public job link",
    screenshot="Upload a screenshot of the job post from your phone"
)
async def slash_apply(
    interaction: discord.Interaction,
    post: Optional[str] = None,
    screenshot: Optional[discord.Attachment] = None
):
    if not await check_interaction_auth(interaction):
        return

    if not post and not screenshot:
        await interaction.response.send_message(
            "⚠️ Please provide either a job post text in `post:` or attach an image in `screenshot:`.",
            ephemeral=True
        )
        return

    await interaction.response.defer()
    raw_text = (post or "").strip()

    if screenshot:
        img_bytes = await screenshot.read()
        ocr_text = await extract_text_from_image_bytes(img_bytes)
        if ocr_text:
            raw_text = f"{raw_text}\n\n{ocr_text}".strip() if raw_text else ocr_text

    if not raw_text:
        await interaction.followup.send("⚠️ Could not detect readable text in the provided input.")
        return

    loop = asyncio.get_running_loop()
    parsed = await loop.run_in_executor(None, parse_raw_job_post, raw_text)

    to_email = parsed.get("recruiter_email", "").strip()
    company = parsed.get("company", "").strip()
    job_title = parsed.get("job_title", "").strip()

    if not to_email:
        # Check if an ATS / Portal or application link was detected
        portal_url = parsed.get("portal_url", "")
        is_portal = parsed.get("is_portal", False)
        portal_name = parsed.get("portal_name", "Online Portal")

        urls_in_post = re.findall(r'https?://[^\s]+', raw_text)
        if not portal_url and urls_in_post:
            portal_url = urls_in_post[0]
            is_portal = True

        if is_portal or portal_url:
            kit = await loop.run_in_executor(
                None,
                lambda: generate_portal_application_kit(
                    company=company or "Target Company",
                    job_title=job_title or "Software Engineer",
                    job_description=raw_text,
                    portal_name=portal_name or "Portal"
                )
            )
            portal_embed = build_portal_kit_embed(kit, raw_url=portal_url)
            await interaction.followup.send(embed=portal_embed)
            return

        no_email_embed = discord.Embed(
            title="⚠️ Recruiter Email Not Found",
            description=(
                f"I parsed the post for **{company}** (`{job_title}`), but could not detect an email address in the text, "
                f"and this company domain was not found in our verified employer directory.\n\n"
                f"💡 **How to proceed:**\n"
                f"• Paste the post again with recruiter email: `Send CV to hr@company.com`\n"
                f"• Or use `/portal company:{company} role:{job_title}` to get a Portal Application Kit!"
            ),
            color=0xF59E0B
        )
        await interaction.followup.send(embed=no_email_embed)
        return

    is_dup = await loop.run_in_executor(None, is_already_applied, to_email, company, job_title)
    embed = build_application_preview(parsed, is_dup)

    view = JobApplicationView(
        parsed_data=parsed,
        raw_post=raw_text,
        author_id=interaction.user.id
    )

    sent_msg = await interaction.followup.send(embed=embed, view=view)
    view.message = sent_msg

@bot.tree.command(name="scan", description="Scan for fresh live job openings and send approval cards to this channel")
async def slash_scan(interaction: discord.Interaction):
    if not await check_interaction_auth(interaction):
        return
    await interaction.response.defer()
    intro_embed = discord.Embed(
        title="🔍 Scanning Live Job Opportunities...",
        description="Searching verified openings matching your profile (Python, Software Engineer, Intern)...",
        color=0x3B82F6
    )
    await interaction.followup.send(embed=intro_embed)
    count = await scan_and_send_leads(interaction.channel, author_id=interaction.user.id)
    if count == 0:
        await interaction.channel.send("✅ You have already applied to all currently scanned opportunities!")
    else:
        await interaction.channel.send(f"📬 Delivered **{count}** new job approval card(s) to this channel!")

@bot.tree.command(name="followup", description="Check applications pending >= 4 days and send 1-click follow-up bump emails")
async def slash_followup(interaction: discord.Interaction):
    if not await check_interaction_auth(interaction):
        return
    await interaction.response.defer()
    loop = asyncio.get_running_loop()
    pending = await loop.run_in_executor(None, lambda: get_pending_followups(min_days=4, max_days=14))

    if not pending:
        embed = discord.Embed(
            title="📬 Application Follow-Up Status",
            description=(
                "🟢 **All applications are up to date!**\n\n"
                "No applications are currently pending >= 4 days without response.\n"
                "The engine automatically alerts you when applications reach the 4-day follow-up window."
            ),
            color=0x22C55E,
            timestamp=datetime.now(timezone.utc)
        )
        await interaction.followup.send(embed=embed)
        return

    intro_embed = discord.Embed(
        title=f"📬 Found {len(pending)} Application(s) Awaiting Follow-Up (>= 4 Days)",
        description="Review the pending applications below. Click **`[🚀 Send Follow-Up Bump]`** to send a polite follow-up with your CV re-attached.",
        color=0x3B82F6,
        timestamp=datetime.now(timezone.utc)
    )
    await interaction.followup.send(embed=intro_embed)

    for rec in pending:
        embed = discord.Embed(
            title=f"⏳ Follow-Up Candidate: {rec['company']}",
            color=0xF59E0B,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="🏢 Company", value=rec["company"], inline=True)
        embed.add_field(name="💼 Role", value=rec["job_title"], inline=True)
        embed.add_field(name="📩 Recipient", value=f"`{rec['recipient_email']}`", inline=True)
        embed.add_field(name="🕒 Applied", value=f"**{rec['days_ago']} days ago** ({rec['timestamp']})", inline=True)
        embed.add_field(name="📝 Original Subject", value=f"`{rec['subject']}`", inline=False)

        view = FollowUpBumpView(record=rec, author_id=interaction.user.id)
        sent_msg = await interaction.channel.send(embed=embed, view=view)
        view.message = sent_msg
        await asyncio.sleep(0.5)

@bot.tree.command(name="portal", description="Generate a copy-paste Portal Application Kit for ATS/NAVTTC forms")
@app_commands.describe(
    company="Company name (e.g. Systems Ltd, Devsinc, NAVTTC)",
    role="Job title (e.g. Associate Software Engineer, Python Intern)",
    portal="Name of portal (e.g. Lever, Greenhouse, NAVTTC NSIS, Rozee)"
)
async def slash_portal(
    interaction: discord.Interaction,
    company: str,
    role: str = "Associate Software Engineer",
    portal: str = "Web Portal"
):
    if not await check_interaction_auth(interaction):
        return
    await interaction.response.defer()
    loop = asyncio.get_running_loop()
    kit = await loop.run_in_executor(
        None,
        lambda: generate_portal_application_kit(company=company, job_title=role, portal_name=portal)
    )
    embed = build_portal_kit_embed(kit)
    await interaction.followup.send(embed=embed)

# ---------------------------------------------------------------------------
# Traditional Prefix (!) Commands (for backwards compatibility)
# ---------------------------------------------------------------------------

@bot.command(name="stats")
async def stats_command(ctx: commands.Context):
    """Displays real-time application tracker statistics."""
    if not is_target_server(ctx.guild):
        return
    async with ctx.typing():
        loop = asyncio.get_running_loop()
        stats = await loop.run_in_executor(None, get_excel_stats)
        embed = build_stats_embed(stats)
        await ctx.send(embed=embed)

@bot.command(name="check")
async def check_command(ctx: commands.Context):
    """Scans Gmail inbox via IMAP for incoming recruiter replies."""
    if not is_target_server(ctx.guild):
        return
    status_msg = await ctx.send("🔍 **Scanning Gmail IMAP inbox for responses from applied companies...**")
    async with ctx.typing():
        loop = asyncio.get_running_loop()
        replies = await loop.run_in_executor(
            None,
            lambda: check_inbound_recruiter_replies(limit=30, notify_discord=False)
        )
        embed = build_check_embed(replies)
        await status_msg.edit(content=None, embed=embed)

@bot.command(name="history")
async def history_command(ctx: commands.Context):
    """Lists the last 5 applications recorded in applied_jobs_tracker.xlsx."""
    if not is_target_server(ctx.guild):
        return
    async with ctx.typing():
        loop = asyncio.get_running_loop()
        records = await loop.run_in_executor(None, lambda: get_recent_applications(limit=5))
        embed = build_history_embed(records)
        await ctx.send(embed=embed)

@bot.command(name="help")
async def help_command(ctx: commands.Context):
    """Provides a clear guide on interacting with the Antigravity Job Assistant bot."""
    if not is_target_server(ctx.guild):
        return
    embed = build_help_embed(ctx.author.id)
    await ctx.send(embed=embed)

@bot.command(name="scan")
async def scan_command(ctx: commands.Context):
    """Scans for fresh job openings and delivers them to this channel for 1-click approval."""
    if not is_target_server(ctx.guild):
        return
    async with ctx.typing():
        count = await scan_and_send_leads(ctx.channel, author_id=ctx.author.id)
        if count == 0:
            await ctx.send("✅ You have already applied to all currently scanned opportunities!")
        else:
            await ctx.send(f"📬 Delivered **{count}** new job approval card(s) to this channel!")

@bot.command(name="followup")
async def followup_command(ctx: commands.Context):
    """Scans tracker for applications pending >= 4 days and presents 1-click follow-up buttons."""
    if not is_target_server(ctx.guild):
        return
    async with ctx.typing():
        loop = asyncio.get_running_loop()
        pending = await loop.run_in_executor(None, lambda: get_pending_followups(min_days=4, max_days=14))

        if not pending:
            embed = discord.Embed(
                title="📬 Application Follow-Up Status",
                description=(
                    "🟢 **All applications are up to date!**\n\n"
                    "No applications are currently pending >= 4 days without response.\n"
                    "The engine automatically alerts you when applications reach the 4-day follow-up window."
                ),
                color=0x22C55E,
                timestamp=datetime.now(timezone.utc)
            )
            await ctx.send(embed=embed)
            return

        intro_embed = discord.Embed(
            title=f"📬 Found {len(pending)} Application(s) Awaiting Follow-Up (>= 4 Days)",
            description="Review the pending applications below. Click **`[🚀 Send Follow-Up Bump]`** to send a polite follow-up with your CV re-attached.",
            color=0x3B82F6,
            timestamp=datetime.now(timezone.utc)
        )
        await ctx.send(embed=intro_embed)

        for rec in pending:
            embed = discord.Embed(
                title=f"⏳ Follow-Up Candidate: {rec['company']}",
                color=0xF59E0B,
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="🏢 Company", value=rec["company"], inline=True)
            embed.add_field(name="💼 Role", value=rec["job_title"], inline=True)
            embed.add_field(name="📩 Recipient", value=f"`{rec['recipient_email']}`", inline=True)
            embed.add_field(name="🕒 Applied", value=f"**{rec['days_ago']} days ago** ({rec['timestamp']})", inline=True)
            embed.add_field(name="📝 Original Subject", value=f"`{rec['subject']}`", inline=False)

            view = FollowUpBumpView(record=rec, author_id=ctx.author.id)
            sent_msg = await ctx.send(embed=embed, view=view)
            view.message = sent_msg
            await asyncio.sleep(0.5)

@bot.command(name="portal")
async def portal_command(ctx: commands.Context, company: str = "Target Employer", *, role: str = "Associate Software Engineer"):
    """Generates ready-to-use answers for portal application forms."""
    if not is_target_server(ctx.guild):
        return
    async with ctx.typing():
        loop = asyncio.get_running_loop()
        kit = await loop.run_in_executor(
            None,
            lambda: generate_portal_application_kit(company=company, job_title=role, portal_name="Web Portal")
        )
        embed = build_portal_kit_embed(kit)
        await ctx.send(embed=embed)

@bot.command(name="navttc")
async def navttc_command(ctx: commands.Context, *, role: str = "Software Engineering Trainee"):
    """Generates tailored application answers for NAVTTC / Prime Minister Youth Program forms."""
    if not is_target_server(ctx.guild):
        return
    async with ctx.typing():
        loop = asyncio.get_running_loop()
        kit = await loop.run_in_executor(
            None,
            lambda: generate_portal_application_kit(company="NAVTTC / Partner Organization", job_title=role, portal_name="NAVTTC NSIS Portal")
        )
        embed = build_portal_kit_embed(kit)
        await ctx.send(embed=embed)

# ---------------------------------------------------------------------------
# Runner Entrypoint
# ---------------------------------------------------------------------------

def run_bot(token: Optional[str] = None):
    """Launches the Discord bot synchronously."""
    bot_token = token or Config.DISCORD_BOT_TOKEN
    if not bot_token:
        print("\n" + "=" * 65)
        print("  [!] ERROR: DISCORD_BOT_TOKEN is not configured!")
        print("=" * 65)
        print("Please add your Discord bot token to your .env file:")
        print("  DISCORD_BOT_TOKEN=your_token_here")
        print("\nSee the Discord Bot Setup Guide in README.md or run with --help.")
        print("=" * 65 + "\n")
        sys.exit(1)

    bot.run(bot_token)

async def start_bot_async(token: Optional[str] = None):
    """Starts the bot asynchronously for concurrent execution with daemon."""
    bot_token = token or Config.DISCORD_BOT_TOKEN
    if not bot_token:
        logger.error("DISCORD_BOT_TOKEN is not configured. Cannot launch Discord bot.")
        return
    await bot.start(bot_token)

if __name__ == "__main__":
    run_bot()
