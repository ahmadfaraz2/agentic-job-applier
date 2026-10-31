# 🤖 Discord Bot Setup & Usage Guide (Agentic Job Outreach Engine)

You can now apply to any job directly from your phone or PC by **pasting a raw LinkedIn post or uploading mobile screenshots into Discord DMs**. The bot will extract all company and role intelligence using Google Antigravity & Gemini 3.8 Flash, show you an interactive preview, and let you dispatch your cold application email with your CV attached with a single click.

---

## ⚡ 2-Minute Quick Setup

### Step 1: Create Your Bot on Discord Developer Portal
1. Open the [Discord Developer Portal](https://discord.com/developers/applications).
2. Click **New Application** (top right), enter a name (e.g. `Job Outreach Assistant`), and click **Create**.
3. In the left sidebar, click on **Bot**.
4. Click **Reset Token** (or **Copy Token**) to copy your secret Bot Token.

### Step 2: Enable "Message Content Intent" (Critical!)
1. Still on the **Bot** page, scroll down to the section titled **Privileged Gateway Intents**.
2. Toggle **ON** the switch for **MESSAGE CONTENT INTENT**.
3. *(Optional but recommended)* Toggle **ON** **SERVER MEMBERS INTENT**.
4. Click **Save Changes** at the bottom.

### Step 3: Invite the Bot to Your Account / Server
1. In the left sidebar, navigate to **Installation** (or **OAuth2 > URL Generator**).
2. Under **Installation Contexts**, check **User Install** and **Guild Install**.
3. Under **Scopes**, select `bot` and `applications.commands`.
4. Under **Bot Permissions**, select:
   - `Send Messages`
   - `Send Messages in Threads`
   - `Embed Links`
   - `Attach Files`
   - `Read Message History`
5. Copy the generated **Install Link** at the bottom, paste it into your browser, and authorize it to your Discord account or private server.

### Step 4: Configure Your `.env` File
Open your `.env` file (`F:\Antigravity-cli\job-automation-smtp\.env`) and paste your token:
```env
# Discord Interactive Bot Configuration
DISCORD_BOT_TOKEN=your_copied_bot_token_here

# (Optional - Locks bot exclusively to your Discord user ID)
DISCORD_OWNER_ID=your_discord_user_id
```

> **How to find your Discord User ID:**
> In Discord, go to **User Settings > Advanced > Enable Developer Mode**.
> Then right-click your profile picture and click **Copy User ID**.

---

## 🚀 How to Run the Bot

### Option 1: Standalone Bot (Recommended for DMs)
```bash
python discord_bot.py
```
*or:*
```bash
python run.py --discord-bot
```

### Option 2: Continuous Background Daemon + Discord Bot
If you want the hourly job scraper daemon and the Discord DM bot running together in the same process:
```bash
python run.py --daemon --discord-bot
```

---

## 💬 How to Use in Discord DMs

1. Open Discord on your phone or desktop.
2. Click on your bot's name to open a **Direct Message (DM)**.
3. Simply **paste any raw LinkedIn post or hiring announcement**!

### Example:
Paste:
```text
Hiring Software Engineering Interns in Lahore. It's paid, with a clear path to a full-time Associate Software Engineer role.

Stack: Django · Node.js · PostgreSQL · MongoDB

To apply: send your CV to hr@devkiosk.com
Subject: SE Intern – [Your Name]
```

### What Happens:
1. **Intelligence Extraction:** Gemini 3.8 Flash extracts:
   - Company: `Devkiosk`
   - Role: `SE Intern`
   - Recruiter Email: `hr@devkiosk.com`
   - Subject Line: `SE Intern – Your Name` (Replaces `[Your Name]` cleanly with your configured sender name)
   - Dynamic Pitch: Highlights your Django, Node.js, PostgreSQL, and MongoDB experience.
2. **Duplicate Check:** Verifies against `applied_jobs_tracker.xlsx`.
3. **Interactive Buttons:**
   - Click **`[🚀 Send Application Email]`**: Sends the application with your CV attached from `data/`, logs to Excel, and updates the Discord message with a green confirmation!
   - Click **`[❌ Cancel]`**: Cancels the application without sending anything.

---

## 🛠️ DM Quick Commands & Slash Commands

You can use either native Discord Slash Commands (`/`) or DM prefix commands (`!`):

| Slash Command | Text Command | Description |
| :--- | :--- | :--- |
| `/apply` | *(Paste post/image)* | Parse a job post and open the 1-click apply preview |
| `/stats` | `!stats` | View total sent applications, interview invites, and unique companies from Excel |
| `/check` | `!check` | Scan Gmail via IMAP for incoming recruiter replies and interview invites |
| `/history` | `!history` | View the last 5 applications sent from your system |
| `/help` | `!help` | Show the user guide and your Discord User ID |
