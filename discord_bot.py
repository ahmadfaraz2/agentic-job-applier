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
from tools.email_tool import send_cv_application_email
from tools.inbox_listener_tool import check_inbound_recruiter_replies
from tools.browser_tool import extract_job_and_email_from_url
from tools.ocr_tool import extract_text_from_image_bytes

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
    """Custom Bot with automated global slash command synchronization."""

    async def setup_hook(self):
        try:
            synced = await self.tree.sync()
            logger.info(f"Successfully synced {len(synced)} application slash command(s) with Discord globally.")
        except Exception as e:
            logger.error(f"Failed to sync slash commands with Discord: {e}", exc_info=True)

bot = AntigravityBot(command_prefix="!", intents=intents, help_command=None)

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
        timeout: float = 900.0  # 15 minutes
    ):
        super().__init__(timeout=timeout)
        self.parsed_data = parsed_data
        self.raw_post = raw_post
        self.author_id = author_id
        self.message: Optional[discord.Message] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "⛔ You are not authorized to interact with this application preview.",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Send Application Email", style=discord.ButtonStyle.success, emoji="🚀")
    async def send_email_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Disable all buttons immediately to prevent duplicate sends
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

        await interaction.response.defer()

        to_email = self.parsed_data.get("recruiter_email", "")
        company = self.parsed_data.get("company", "")
        job_title = self.parsed_data.get("job_title", "")
        subject_line = self.parsed_data.get("subject_line", "")
        pitch = self.parsed_data.get("tailored_pitch", "")

        # Dispatch application email in background executor
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            send_cv_application_email,
            to_email,
            job_title,
            company,
            pitch,
            self.raw_post,
            "LinkedIn / Discord",
            True,  # force=True because user explicitly clicked confirm
            subject_line
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

            await interaction.edit_original_response(embed=embed, view=self)
        else:
            fail_embed = discord.Embed(
                title="⚠️ Application Dispatch Failed",
                description=f"Encountered an issue dispatching email:\n```\n{result}\n```",
                color=0xEF4444,
                timestamp=datetime.now(timezone.utc)
            )
            await interaction.edit_original_response(embed=fail_embed, view=self)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
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
        await interaction.response.edit_message(embed=cancel_embed, view=self)

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

# ---------------------------------------------------------------------------
# Helper: Security & Permissions Verification
# ---------------------------------------------------------------------------

def is_authorized_user(user: discord.User | discord.Member) -> bool:
    """Verifies that the user is the owner (Ahmad Faraz) if DISCORD_OWNER_ID is set."""
    if not Config.DISCORD_OWNER_ID:
        return True
    return str(user.id) == str(Config.DISCORD_OWNER_ID).strip()

async def check_interaction_auth(interaction: discord.Interaction) -> bool:
    """Checks slash command permission."""
    if not is_authorized_user(interaction.user):
        await interaction.response.send_message(
            "⛔ **Unauthorized:** This bot is exclusively configured for Ahmad Faraz.",
            ephemeral=True
        )
        return False
    return True

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
            "2. 📝 **Drop Raw Text:** Paste unformatted hiring announcements or job descriptions directly into this chat.\n"
            "3. ⚡ **Slash Command:** Type `/apply` to provide post text or upload a screenshot with auto-complete!\n\n"
            "### ⚡ What Happens Next:\n"
            "• **Gemini 3.8 Flash Analysis:** Extracts Company, Role, Recruiter Email, and exact Subject requirements.\n"
            "• **Interactive Preview:** The bot formats an embed with all parsed information.\n"
            "• **1-Click Dispatch:** Click **`[🚀 Send Application Email]`** to send your cold email with `Ahmad_Faraz_CV.pdf` attached.\n\n"
            "### 🛠️ Slash (/) & Prefix (!) Commands:\n"
            "• `/apply` (or paste post) — Apply to a job post or screenshot.\n"
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

def build_application_preview(parsed: Dict[str, Any], is_dup: bool) -> discord.Embed:
    company = parsed.get("company", "")
    job_title = parsed.get("job_title", "")
    to_email = parsed.get("recruiter_email", "")
    location = parsed.get("location", "") or "On-site / Remote"
    subject_line = parsed.get("subject_line", "")
    tailored_pitch = parsed.get("tailored_pitch", "")
    model_engine = parsed.get("model_engine", "Gemini 3.8 Flash")

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
    embed.add_field(name="📩 Recruiter Email", value=f"`{to_email}`", inline=False)
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
# Bot Events
# ---------------------------------------------------------------------------

@bot.event
async def on_ready():
    logger.info(f"Antigravity Discord Bot logged in as: {bot.user} (ID: {bot.user.id})")
    print("\n" + "=" * 65)
    print(f"  🤖 ANTIGRAVITY DISCORD OUTREACH BOT IS ONLINE!")
    print(f"  • Bot Account: {bot.user}")
    print(f"  • Connected:   {len(bot.guilds)} server(s)")
    if Config.DISCORD_OWNER_ID:
        print(f"  • Owner Lock:  Authorized User ID: {Config.DISCORD_OWNER_ID}")
    else:
        print("  • Owner Lock:  Open to direct DMs (Set DISCORD_OWNER_ID to lock)")
    print("=" * 65 + "\n")
    activity = discord.Activity(type=discord.ActivityType.watching, name="LinkedIn jobs & screenshots")
    await bot.change_presence(activity=activity)

@bot.event
async def on_message(message: discord.Message):
    # Ignore messages from bots (including self)
    if message.author.bot:
        return

    logger.info(
        f"Incoming message from {message.author} (ID: {message.author.id}) in {type(message.channel).__name__} "
        f"(guild={message.guild}): content='{message.content[:60]}', attachments={len(message.attachments)}"
    )

    # Check authorization
    if not is_authorized_user(message.author):
        logger.warning(f"Blocked unauthorized message from {message.author} (ID: {message.author.id})")
        if message.guild is None or isinstance(message.channel, discord.DMChannel):
            await message.channel.send("⛔ **Unauthorized:** This bot is exclusively configured for Ahmad Faraz.")
        return

    # Process standard prefix commands first (e.g. !stats, !check, !history, !help)
    if message.content.strip().startswith("!"):
        await bot.process_commands(message)
        return

    # If message is received in DMs, treat it as a raw job post, screenshot, or URL
    if message.guild is None or isinstance(message.channel, discord.DMChannel):
        await handle_incoming_job_post(message)
        return

    # If in a guild channel, allow bot if explicitly mentioned
    if bot.user in message.mentions:
        clean_text = message.content.replace(f"<@{bot.user.id}>", "").strip()
        message.content = clean_text
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
            no_email_embed = discord.Embed(
                title=f"⚠️ Recruiter Email Not Found",
                description=(
                    f"I parsed the post for **{company}** (`{job_title}`), but could not detect an email address in the text.\n\n"
                    f"💡 **How to proceed:**\n"
                    f"Paste the post again and append the recruiter's email at the end:\n"
                    f"*(e.g., `Send CV to hr@company.com`)*"
                ),
                color=0xF59E0B
            )
            no_email_embed.add_field(name="🏢 Detected Company", value=company or "Unknown", inline=True)
            no_email_embed.add_field(name="💼 Detected Role", value=job_title or "Unknown", inline=True)
            no_email_embed.set_footer(text=f"Engine: {parsed.get('model_engine', 'Gemini 3.8 Flash')}")

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
        no_email_embed = discord.Embed(
            title="⚠️ Recruiter Email Not Found",
            description=f"I parsed the post for **{company}** (`{job_title}`), but could not detect an email address in the text.",
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

# ---------------------------------------------------------------------------
# Traditional Prefix (!) Commands (for backwards compatibility)
# ---------------------------------------------------------------------------

@bot.command(name="stats")
async def stats_command(ctx: commands.Context):
    """Displays real-time application tracker statistics."""
    async with ctx.typing():
        loop = asyncio.get_running_loop()
        stats = await loop.run_in_executor(None, get_excel_stats)
        embed = build_stats_embed(stats)
        await ctx.send(embed=embed)

@bot.command(name="check")
async def check_command(ctx: commands.Context):
    """Scans Gmail inbox via IMAP for incoming recruiter replies."""
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
    async with ctx.typing():
        loop = asyncio.get_running_loop()
        records = await loop.run_in_executor(None, lambda: get_recent_applications(limit=5))
        embed = build_history_embed(records)
        await ctx.send(embed=embed)

@bot.command(name="help")
async def help_command(ctx: commands.Context):
    """Provides a clear guide on interacting with the Antigravity Job Assistant bot."""
    embed = build_help_embed(ctx.author.id)
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
