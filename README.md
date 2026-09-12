# ✨ VibeCoder • Autonomous Vibe Coding Control Center

An autonomous, multi-engine AI coding system running inside GitHub Codespaces with a **Telegram Control Center UI**, project management, git tracking, test verification, and automated Codespace migration transport.

---

## 🚀 Key Features

- **Multi-Engine AI Architecture**:
  1. **Google DeepMind Antigravity CLI** (`agy`): Powered by **Gemini 3.8 Flash (High)** with 1M context, multi-file reasoning, and auto-approval tools.
  2. **GitHub Copilot CLI** (`copilot`): Powered by **Student Plan (Auto Dynamic / Luna)** with system shell and file editing tools.
  3. **Aider CLI** (`aider`): Powered by **OpenRouter API Key** (e.g. DeepSeek Chat, Gemini 2.0 Flash, Claude 3.5 Sonnet) with repo-map AST parsing.
  4. **Auto Vibe (Ensemble Mode)**: Autonomous self-healing loop: **Plan (Gemini 3.8) ➔ Edit Code ➔ Run Automated Tests ➔ Auto-Fix on Error**.

- **Project & Workspace Management**:
  - **Existing Folders**: Switch between any folder or repository in the Codespace.
  - **GitHub Links**: Clone any repository with one command: `/clone <url>`
  - **New Projects**: 1-click scaffolding with templates for:
    - 🐍 **Python FastAPI** (with REST endpoints & `pytest` suite)
    - 💻 **Python CLI** (with `argparse` & tests)
    - 🟢 **Node Express** (with `package.json`)
    - 🌐 **Modern Web** (HTML5, modern CSS, vanilla JS)
    - 📄 **Blank Project** (clean initialized Git repository)

- **Telegram Interface & Control Center UI**:
  - Rich interactive Dashboard with inline buttons
  - Natural Language Vibe Coding: Just send any text or voice message
  - Real-time progress updates & live typing indicators
  - Formatted Git Diff cards with monospaced code blocks
  - 1-Click Commit, Git Push, and Hard Revert
  - Safe terminal command execution with `/sh <command>`
  - Automated test runner with `/test`

- **Codespace Transport & Zero-Loss Migration**:
  - Automatically packages all projects, code edits, `.env` configs, and AI settings into `vibecoder_backup_latest.tar.gz`.
  - **Telegram Document Backup**: Sends the complete compressed backup directly to your private Telegram chat!
  - **1-Click Restore**: Paste a single command in your **NEW CODESPACE** to restore all projects and configs in seconds!
  - **GitHub Sync**: Push backup snapshots to a dedicated GitHub branch.

---

## 📱 Telegram Interface Overview

```text
✨ 𝗩𝗜𝗕𝗘 𝗖𝗢𝗗𝗘𝗥 • 𝗔𝘂𝘁𝗼𝗻𝗼𝗺𝗼𝘂𝘀 𝗦𝘁𝘂𝗱𝗶𝗼
─────────────────────────────
📂 Active Project: demo_app
🌿 Git Branch: main 🟢
📊 Worktree: Branch 'main' is clean.
📁 Files: 4 files in project
🤖 AI Engine: Antigravity (Gemini 3.8 Flash High)
⏱ Codespace: Online 🟢
─────────────────────────────
💡 Send any message or prompt to vibe code autonomously!
Tap buttons below to switch projects, engines, or git actions.
```

### Dashboard Buttons:
- `[ 🚀 Vibe Coding ]` `[ 🤖 Switch Engine ]`
- `[ 📂 Projects ]` `[ ➕ New Project ]`
- `[ 🔗 Clone Repo ]` `[ 📊 Git & Diff ]`
- `[ 🧪 Run Tests ]` `[ 💻 Shell Runner ]`
- `[ 📦 Backup & Migrate ]` `[ ⚙️ Settings ]`

---

## ⚡ Quick Start

### 1. Configure Telegram Bot Token
You can create a free bot token via [@BotFather](https://t.me/BotFather) on Telegram, or configure an existing token:
```bash
./set_vibe_token.sh <YOUR_TELEGRAM_BOT_TOKEN> [YOUR_OWNER_ID]
```

### 2. Launch VibeCoder
- **Run in Foreground**:
  ```bash
  ./run_vibecoder.sh
  ```
- **Run in Background (Daemon)**:
  ```bash
  ./run_vibecoder.sh --daemon
  ```
- **Check Status**:
  ```bash
  ./run_vibecoder.sh --status
  ```
- **Stream Logs**:
  ```bash
  ./run_vibecoder.sh --logs
  ```
- **Stop Daemon**:
  ```bash
  ./run_vibecoder.sh --stop
  ```
- **Interactive Terminal CLI Mode** (No Telegram needed):
  ```bash
  ./run_vibecoder.sh --cli
  ```

---

## 📦 Codespace Migration (When Credits Run Out)

### Step 1: Export from Old Codespace
In Telegram, tap `📦 Backup & Migrate` ➔ `📤 Send Backup File to Chat`, or run in terminal:
```bash
./transport.sh backup
```

### Step 2: Restore in New Codespace
In your new Codespace terminal, run:
```bash
bash transport.sh restore /path/to/vibecoder_backup_latest.tar.gz
```
Or if you have a download URL:
```bash
bash transport.sh restore <URL>
```

---

## 🧪 Testing

Run the full automated test suite anytime:
```bash
python3 -m pytest -v vibecoder/tests/test_all.py
```
