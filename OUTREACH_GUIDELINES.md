# 📜 Ahmad Faraz — Professional Outreach & Job Application Guidelines

> **Status:** Active Standard & Core Directive for Antigravity AI Agents & Parsers  
> **Target Candidate:** Ahmad Faraz (`dev.ahmadfaraz24@gmail.com`)  
> **Applies to:** Email Dispatch, Pitch Generation, Subject Line Formulation, Raw Post Parsing  

---

## 🚫 1. STRICT ZERO-EMOJI DIRECTIVE (ABSOLUTE)

Cold outreach and job application emails containing emojis look like spam, promotional newsletters, or automated AI bot slop.

### Strict Rules:
- **NEVER use emojis in subject lines.** (e.g., No 🚀, 🔥, 💼, 📌, ✉️, 🟢).
- **NEVER use emojis in email bodies or greetings.** (e.g., No 👋, ✨, 🎯, 👍).
- **NEVER use emojis in job titles or company names.** Strip any recruiter bullets or keycaps like `1️⃣`, `2️⃣`, `🔹`, `→`, `•`.
- **Always run automated emoji sanitization** across all outgoing content prior to SMTP delivery.

---

## 🧠 2. MODEL THINKING & STEP-BY-STEP REASONING CHAIN

When ingesting a raw job post, the model / parser must deliberately reason through the following 6-step cognitive chain before producing any application draft:

### Step 1: Sanitize & Pre-process Input
- Strip all Unicode emojis, pictographs, dingbats, and keycaps (`1️⃣`, `👉`, `🚀`).
- Strip leading bullet symbols (`→`, `•`, `-`, `*`).
- Normalize special dashes (`–`, `—`) into clean standard hyphens (`-`).

### Step 2: Resolve True Company Entity vs Poster's Name
- LinkedIn posts often begin with the poster's personal name (e.g. `Mehak Azam`, `Senior HR at KaveLogics`).
- **Do not mistake the recruiter's personal name for the company name.**
- If the text mentions `"at [Company]"` or the email domain is corporate (e.g. `careers@kavelogics.com`), the true company is `KaveLogics`, **not** `Mehak Azam`.
- Check against known company dictionaries and normalize casing (e.g., `systemsltd.com` &rarr; `Systems Limited`).

### Step 3: Identify Genuine Job Title vs Employment Details
- Distinguish the **Job Title** from contract duration, stipend, or shift details.
- **Bad / Flawed:** `"→ 2–3 Month Paid Internship"` (This is contract duration, not a title).
- **Good / Genuine:** `"SE Intern"`, `"Software Engineering Intern"`, `"Associate Python Engineer"`.
- Reject any candidate title containing duration or compensation words (`month`, `year`, `paid`, `stipend`, `pkr`, `salary`, `converts to`, `timings`, `shift`).
- Convert plural job titles to singular (`Interns` &rarr; `Intern`, `Developers` &rarr; `Developer`).

### Step 4: Detect & Enforce Recruiter-Mandated Subject Lines
Recruiters often have automated filters or Gmail rules that require specific subject lines.
- Look for patterns like `Subject: ...`, `Subject line: ...`, or `Mention "..." in subject`.
- Replace candidate placeholders (`[Your Name]`, `<Your Name>`, `{Your Name}`, `[Name]`, `Your Name`) with `Ahmad Faraz`.
- Replace role placeholders (`[Role]`, `[Position]`, `[Job Title]`) with the detected title.
- If recruiter specified `Subject: SE Intern – [Your Name]`, the subject line **must be**:  
  `SE Intern - Ahmad Faraz` (with ZERO emojis).
- If no specific subject was requested, default to:  
  `Application for [Job Title] - Ahmad Faraz`.

### Step 5: Dynamic Stack Alignment (Humanized & Grounded)
Never use generic AI buzzword soup or claim skills not in Ahmad Faraz's real repertoire.
- **Ahmad Faraz's Verified Stack:**
  - **Languages & Frameworks:** Python (Django, FastAPI), JavaScript (React), Node.js fundamentals.
  - **Databases:** PostgreSQL, MongoDB, SQL.
  - **AI Developer Workflows:** Cursor, Claude Code, GitHub Copilot.
  - **Testing & QA:** Playwright, Selenium, REST API testing, debugging.
  - **Work Ethic:** Strong project ownership, ability to work solo without hand-holding.
- Inspect the post for matching keywords and weave them naturally into the middle paragraph.
- If the post asks for Django, Node.js, and MongoDB, highlight those specifically.
- If the post asks for Playwright and QA, focus on automation and edge-case discovery.
- Avoid false positive substring triggers (e.g. `"ai"` matching inside `"paid"` or `"email"`).

### Step 6: Compose 100% Organic Plain Text
- Keep the email concise, humble, respectful, and direct (under 120 words).
- Pure plain text (`text/plain`). No HTML cards, no color blocks, no bot markers.
- Reference attached CV: [`data/Ahmad_Faraz_CV.pdf`](file:///F:/Antigravity-cli/job-automation-smtp/data/Ahmad_Faraz_CV.pdf).
- Standard clean signature:
  ```text
  Regards,
  Ahmad Faraz
  +92 307 5709318
  LinkedIn: https://www.linkedin.com/in/ahmad-faraz-/
  GitHub: https://github.com/ahmadfaraz2
  ```

---

## 🛡️ 3. ANTI-DUPLICATION GUARD
- Every proposed application must be checked against [`data/applied_jobs_tracker.xlsx`](file:///F:/Antigravity-cli/job-automation-smtp/data/applied_jobs_tracker.xlsx).
- If `(recipient_email, company)` exists in the tracker, **block duplicate outreach** unless the user explicitly forces it.
