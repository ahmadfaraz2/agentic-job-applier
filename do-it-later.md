# 📌 Do It Later (Backlog)

## 1. Personal LinkedIn Integration via Browser CDP (Recommended & Safest)

### 🎯 Objective
Connect the Antigravity agent to an active, logged-in Google Chrome or Microsoft Edge browser session via the **Chrome DevTools Protocol (CDP)** on port `9222` to scan personal feeds, connections, and hiring posts.

---

### 🛡️ Why Browser CDP is the Safest Approach
- **No Password or Token Storage**: You never store your LinkedIn password or `li_at` cookie in plain text.
- **Bypasses Bot Checkpoints**: Because it runs inside a real browser instance with your existing cookies and human fingerprint, LinkedIn's anti-bot/CAPTCHA mechanisms are not triggered.
- **Human In The Loop**: If a security verification or CAPTCHA ever appears, you can solve it directly in the open browser window, and the agent continues.

---

### 💡 Future Use Cases
1. **Feed & Hiring Post Scanning**:
   - Automatically detect organic posts from connections/founders announcing openings (e.g., *"We're hiring a Junior/Associate Python Developer in Lahore"*).
2. **Recruiter Post Extraction**:
   - Parse posts by recruiters asking candidates to email their CVs to specific addresses (e.g., `careers@company.com`).
3. **Automated Application Handoff**:
   - Feed discovered contact emails directly into `send_cv_application_email` to apply instantly in Ahmad Faraz's authentic organic plain-text voice with `Ahmad_Faraz_CV.pdf` attached.

---

### 🛠️ Planned Implementation Steps

1. **Browser Launcher Shortcut**:
   Add a helper script (`scripts/launch-browser-cdp.bat` or `.ps1`) that launches Chrome with remote debugging:
   ```cmd
   "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%LOCALAPPDATA%\Google\Chrome\User Data"
   ```

2. **CDP Connector in `tools/browser_tool.py`**:
   Extend `check_cdp_available()` to connect via WebSocket to `http://127.0.0.1:9222/json/version` and control the active LinkedIn tab.

3. **Feed & Post Parser**:
   Read the live DOM of `https://www.linkedin.com/feed/` to extract posts containing hiring keywords (`hiring`, `intern`, `associate engineer`, `apply at`, `send cv to`).
