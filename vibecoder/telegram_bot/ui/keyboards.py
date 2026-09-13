"""
Inline Keyboard layouts and interactive UI elements for VibeCoder Telegram Bot.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Dict, Any

def main_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("🚀 Vibe Coding", callback_data="vibe_help"),
            InlineKeyboardButton("🤖 Switch Engine", callback_data="menu_engines")
        ],
        [
            InlineKeyboardButton("📂 Projects", callback_data="menu_projects"),
            InlineKeyboardButton("➕ New Project", callback_data="menu_new_project")
        ],
        [
            InlineKeyboardButton("🔗 Clone Repo", callback_data="menu_clone_repo"),
            InlineKeyboardButton("📊 Git & Diff", callback_data="menu_git")
        ],
        [
            InlineKeyboardButton("🧪 Run Tests", callback_data="action_run_tests"),
            InlineKeyboardButton("💻 Shell Runner", callback_data="menu_shell")
        ],
        [
            InlineKeyboardButton("📦 Backup & Migrate", callback_data="menu_backup"),
            InlineKeyboardButton("🔐 Auth & Accounts", callback_data="menu_auth")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def engine_selection_keyboard(engines: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    keyboard = []
    for eng in engines:
        mark = "✅ " if eng["is_active"] else "   "
        btn_text = f"{mark}{eng['name']} - {eng['description'][:25]}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"set_engine:{eng['id']}")])

    keyboard.append([InlineKeyboardButton("🏠 Back to Dashboard", callback_data="menu_dashboard")])
    return InlineKeyboardMarkup(keyboard)

def project_selection_keyboard(projects: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    keyboard = []
    for idx, p in enumerate(projects[:8]):
        mark = "✅ " if p["is_active"] else "   "
        btn_text = f"{mark}{p['name']} ({p['branch']})"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"select_proj:{idx}")])

    keyboard.append([
        InlineKeyboardButton("➕ New Project", callback_data="menu_new_project"),
        InlineKeyboardButton("🔗 Clone Repo", callback_data="menu_clone_repo")
    ])
    keyboard.append([InlineKeyboardButton("🏠 Back to Dashboard", callback_data="menu_dashboard")])
    return InlineKeyboardMarkup(keyboard)

def template_selection_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("🐍 Python FastAPI", callback_data="new_tmpl:python"),
            InlineKeyboardButton("💻 Python CLI", callback_data="new_tmpl:cli")
        ],
        [
            InlineKeyboardButton("🟢 Node Express", callback_data="new_tmpl:node"),
            InlineKeyboardButton("🌐 Modern Web", callback_data="new_tmpl:web")
        ],
        [
            InlineKeyboardButton("📄 Blank Project", callback_data="new_tmpl:blank")
        ],
        [
            InlineKeyboardButton("🏠 Back to Dashboard", callback_data="menu_dashboard")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def vibe_result_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("📝 View Diff", callback_data="git_view_diff"),
            InlineKeyboardButton("✅ Commit Changes", callback_data="git_commit_quick")
        ],
        [
            InlineKeyboardButton("🧪 Run Tests", callback_data="action_run_tests"),
            InlineKeyboardButton("🧹 New Session", callback_data="session_reset")
        ],
        [
            InlineKeyboardButton("⏪ Revert Code", callback_data="git_revert_confirm"),
            InlineKeyboardButton("🏠 Main Dashboard", callback_data="menu_dashboard")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def git_menu_keyboard(has_changes: bool = True) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("📝 View Diff", callback_data="git_view_diff"),
            InlineKeyboardButton("✅ Commit All", callback_data="git_commit_quick")
        ],
        [
            InlineKeyboardButton("⬇️ Git Pull (Update)", callback_data="git_pull"),
            InlineKeyboardButton("⬆️ Git Push", callback_data="git_push")
        ],
        [
            InlineKeyboardButton("🐙 GitHub Publish", callback_data="git_publish"),
            InlineKeyboardButton("⏪ Revert to HEAD", callback_data="git_revert_confirm")
        ],
        [
            InlineKeyboardButton("🔄 Refresh Status", callback_data="menu_git"),
            InlineKeyboardButton("🏠 Dashboard", callback_data="menu_dashboard")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def backup_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("📤 Send Backup File to Chat", callback_data="backup_send_doc"),
        ],
        [
            InlineKeyboardButton("☁️ 1-Click Cloud Restore Link", callback_data="backup_cloud_link"),
        ],
        [
            InlineKeyboardButton("🐙 Push Backup to GitHub", callback_data="backup_sync_git"),
        ],
        [
            InlineKeyboardButton("🏠 Main Dashboard", callback_data="menu_dashboard")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def confirm_revert_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("⚠️ YES, Revert All Changes", callback_data="git_do_revert"),
            InlineKeyboardButton("❌ Cancel", callback_data="menu_git")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def auth_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("🐙 Login Copilot (Device Code)", callback_data="auth_copilot_device")
        ],
        [
            InlineKeyboardButton("🐙 Enter Copilot Token / PAT", callback_data="auth_copilot_token_prompt"),
            InlineKeyboardButton("🧠 Replace Gemini Auth", callback_data="auth_gemini_prompt")
        ],
        [
            InlineKeyboardButton("⚡ Replace OpenRouter Key", callback_data="auth_openrouter_prompt"),
            InlineKeyboardButton("🔄 Refresh Status", callback_data="menu_auth")
        ],
        [
            InlineKeyboardButton("🏠 Main Dashboard", callback_data="menu_dashboard")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def copilot_device_keyboard(verification_url: str) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("🌐 Open GitHub Authorization Page", url=verification_url)
        ],
        [
            InlineKeyboardButton("🔄 Check Authorization", callback_data="menu_auth"),
            InlineKeyboardButton("❌ Cancel", callback_data="menu_auth")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

