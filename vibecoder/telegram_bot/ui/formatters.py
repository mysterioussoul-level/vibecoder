"""
HTML Message formatting and UI presentation for VibeCoder Telegram Bot.
Safe escaping prevents Telegram Markdown/HTML parse errors.
"""

import html
from typing import Dict, Any, Optional
from vibecoder.core.engines.base import EngineResult
from vibecoder.core.test_runner import TestReport
from vibecoder.config import CODESPACE_NAME

def escape(text: Any) -> str:
    """Safely escape text for Telegram HTML mode."""
    if text is None:
        return ""
    return html.escape(str(text))

def format_dashboard(project: Dict[str, Any], engine_name: str, git_st: Dict[str, Any]) -> str:
    p_name = escape(project.get("name", "None"))
    branch = escape(git_st.get("branch", "none"))
    st_summary = escape(git_st.get("summary", "Clean"))
    eng_esc = escape(engine_name)
    cs_name = escape(CODESPACE_NAME)

    status_icon = "🟢" if git_st.get("clean", True) else "🟡"
    files_count = project.get("files_count", 0)

    msg = (
        "✨ <b>𝗩𝗜𝗕𝗘 𝗖𝗢𝗗𝗘𝗥 • 𝗔𝘂𝘁𝗼𝗻𝗼𝗺𝗼𝘂𝘀 𝗦𝘁𝘂𝗱𝗶𝗼</b>\n"
        "─────────────────────────────\n"
        f"📂 <b>Active Project:</b> <code>{p_name}</code>\n"
        f"🌿 <b>Git Branch:</b> <code>{branch}</code> {status_icon}\n"
        f"📊 <b>Worktree:</b> {st_summary}\n"
        f"📁 <b>Files:</b> {files_count} files in project\n"
        f"🤖 <b>AI Engine:</b> <b>{eng_esc}</b>\n"
        f"🛰 <b>Codespace:</b> <code>{cs_name}</code> 🟢\n"
        "─────────────────────────────\n"
        "💡 <i>Send any message or prompt to vibe code autonomously!</i>\n"
        "<i>Tap buttons below to switch projects, engines, or git actions.</i>"
    )
    return msg

def format_vibe_result(res: EngineResult) -> str:
    status_icon = "✅" if res.success else "❌"
    title = "𝗩𝗶𝗯𝗲 𝗖𝗼𝗱𝗶𝗻𝗴 𝗖𝗼𝗺𝗽𝗹𝗲𝘁𝗲!" if res.success else "𝗩𝗶𝗯𝗲 𝗖𝗼𝗱𝗶𝗻𝗴 𝗙𝗮𝗶𝗹𝗲𝗱"
    eng_esc = escape(res.engine)
    dur = round(res.duration, 1)

    parts = [
        f"{status_icon} <b>{title}</b>\n"
        "─────────────────────────────\n"
        f"🤖 <b>Engine:</b> {eng_esc}\n"
        f"⏱ <b>Execution Time:</b> {dur}s\n"
    ]

    if res.modified_files:
        files_str = "\n".join(f"• <code>{escape(f)}</code>" for f in res.modified_files[:8])
        if len(res.modified_files) > 8:
            files_str += f"\n<i>...and {len(res.modified_files) - 8} more</i>"
        parts.append(f"📝 <b>Modified Files:</b>\n{files_str}\n")
    else:
        parts.append("📝 <b>Modified Files:</b> No file changes detected.\n")

    if res.diff_stat:
        parts.append(f"📊 <b>Diff Stat:</b>\n<pre>{escape(res.diff_stat[:400])}</pre>\n")

    if res.test_report:
        t_icon = "✅" if res.test_report.passed else "❌"
        parts.append(
            f"🧪 <b>Automated Tests ({escape(res.test_report.runner)}):</b> {t_icon}\n"
            f"<i>{escape(res.test_report.summary)}</i>\n"
        )

    if res.error:
        parts.append(f"⚠️ <b>Failure Diagnosis:</b>\n<pre>{escape(res.error[:800])}</pre>\n")
        parts.append("💡 <i>Tip: Tap /engines to switch to GitHub Copilot or Aider, or inspect with /test.</i>\n")
    elif not res.success and not res.modified_files:
        parts.append("⚠️ <b>Notice:</b> The AI engine completed its reasoning pass but did not make code edits.\n")
        parts.append("💡 <i>Tip: Tap /engines to switch to GitHub Copilot or Aider, or be more explicit in your request.</i>\n")
    elif res.output:
        summary_out = res.output.strip()
        if len(summary_out) > 500:
            summary_out = summary_out[:500] + "..."
        parts.append(f"💬 <b>AI Summary:</b>\n<i>{escape(summary_out)}</i>\n")

    parts.append("─────────────────────────────\n👇 <i>What would you like to do next?</i>")
    return "\n".join(parts)

def format_diff_view(diff_text: str, project_name: str) -> str:
    escaped_diff = escape(diff_text[:3500])
    return (
        f"📝 <b>Git Diff • {escape(project_name)}</b>\n"
        "─────────────────────────────\n"
        f"<pre>{escaped_diff}</pre>"
    )

def format_test_report_view(report: TestReport, project_name: str) -> str:
    t_icon = "✅ Passed" if report.passed else "❌ Failed"
    return (
        f"🧪 <b>Test Execution Report • {escape(project_name)}</b>\n"
        "─────────────────────────────\n"
        f"Runner: <code>{escape(report.runner)}</code>\n"
        f"Status: <b>{t_icon}</b> ({round(report.duration, 2)}s)\n"
        f"Summary: <i>{escape(report.summary)}</i>\n\n"
        "<b>Output Details:</b>\n"
        f"<pre>{escape(report.output[:3000])}</pre>"
    )

def format_backup_info(backup_path: str, size: str) -> str:
    return (
        "📦 <b>Codespace Transport & Backup</b>\n"
        "─────────────────────────────\n"
        f"Current Archive: <code>{escape(backup_path)}</code>\n"
        f"Archive Size: <b>{escape(size)}</b>\n\n"
        "💡 <i>If your Codespace runs out of hours or credits, you can transport this complete workspace to any new Codespace in seconds!</i>"
    )

def format_auth_status(status: Dict[str, Any]) -> str:
    g = status.get("gemini", {})
    c = status.get("copilot", {})
    o = status.get("openrouter", {})

    return (
        "🔐 <b>AI Engines & Authentication Status</b>\n"
        "─────────────────────────────\n"
        f"🧠 <b>Google Antigravity (Gemini 3.8):</b> {g.get('status', 'Unknown')}\n"
        f"<i>{escape(g.get('details', ''))}</i>\n\n"
        f"🐙 <b>GitHub Copilot (Student / Auto):</b> {c.get('status', 'Unknown')}\n"
        f"<i>{escape(c.get('details', ''))}</i>\n\n"
        f"⚡ <b>OpenRouter (Aider):</b> {o.get('status', 'Unknown')}\n"
        f"<i>{escape(o.get('details', ''))}</i>\n"
        "─────────────────────────────\n"
        "💡 <i>If any token expires or credits are exhausted, tap below to re-authenticate or log in directly through Telegram!</i>"
    )

