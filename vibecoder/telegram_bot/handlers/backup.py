"""
Workspace Backup and Migration handlers for VibeCoder Telegram Bot.
Enables instant transportation of the workspace to another Codespace.
"""

import subprocess
import os
from pathlib import Path
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from vibecoder.config import WORKSPACE_ROOT
from vibecoder.telegram_bot.ui.keyboards import backup_menu_keyboard, main_menu_keyboard
from vibecoder.telegram_bot.ui.formatters import escape
from vibecoder.telegram_bot.handlers.start import is_authorized

TRANSPORT_SCRIPT = WORKSPACE_ROOT / "transport.sh"

async def backup_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        return

    text = (
        "📦 <b>Codespace Transport & Migration</b>\n"
        "─────────────────────────────\n"
        "If your Codespace credits or monthly free hours run out, you can transport "
        "your entire workspace (all projects, git history, settings, and bot) to a new Codespace in seconds!\n\n"
        "Choose an export method:"
    )

    markup = backup_menu_keyboard()
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)

async def send_backup_document_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_authorized(query.from_user.id):
        return

    status_msg = await query.message.reply_text("📦 <i>Creating compressed workspace backup package...</i>", parse_mode=ParseMode.HTML)

    proc = subprocess.run([str(TRANSPORT_SCRIPT), "backup"], capture_output=True, text=True)
    latest_archive = WORKSPACE_ROOT / "vibecoder_backup_latest.tar.gz"

    if not latest_archive.exists():
        await status_msg.edit_text("❌ Backup creation failed.", parse_mode=ParseMode.HTML)
        return

    file_size_mb = round(latest_archive.stat().st_size / (1024 * 1024), 2)
    await status_msg.edit_text(f"📤 <i>Uploading backup file ({file_size_mb} MB) to Telegram...</i>", parse_mode=ParseMode.HTML)

    try:
        with open(latest_archive, "rb") as f:
            caption = (
                "📦 <b>VibeCoder Complete Workspace Backup</b>\n\n"
                "To restore in a <b>new Codespace</b>:\n"
                "1. Upload or copy this file to <code>/workspaces/playground/</code>\n"
                "2. Run:\n"
                "<code>tar -xzf vibecoder_backup_latest.tar.gz -C /workspaces/playground/ && bash /workspaces/playground/transport.sh restore-env</code>"
            )
            await context.bot.send_document(
                chat_id=query.message.chat_id,
                document=f,
                filename="vibecoder_backup_latest.tar.gz",
                caption=caption,
                parse_mode=ParseMode.HTML
            )
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text(f"❌ Failed to upload document: {escape(str(e))}", parse_mode=ParseMode.HTML)

async def export_cloud_link_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_authorized(query.from_user.id):
        return

    status_msg = await query.message.reply_text("☁️ <i>Creating backup and uploading to cloud transfer service...</i>", parse_mode=ParseMode.HTML)

    proc = subprocess.run([str(TRANSPORT_SCRIPT), "export"], capture_output=True, text=True)
    out = proc.stdout + "\n" + proc.stderr

    lines = out.splitlines()
    cmd_line = ""
    for line in lines:
        if "curl -sSL" in line and "tar -xzf" in line:
            cmd_line = line.strip()
            break

    if cmd_line:
        resp = (
            "🚀 <b>1-Click Codespace Restore Command</b>\n"
            "─────────────────────────────\n"
            "Paste this single command into the terminal of your <b>NEW CODESPACE</b>:\n\n"
            f"<pre><code>{escape(cmd_line)}</code></pre>\n\n"
            "<i>Everything (projects, code changes, and AI configuration) will be restored instantly!</i>"
        )
    else:
        resp = f"📦 <b>Export Log:</b>\n<pre>{escape(out[:2500])}</pre>"

    await status_msg.edit_text(resp, reply_markup=main_menu_keyboard(), parse_mode=ParseMode.HTML)

async def sync_github_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_authorized(query.from_user.id):
        return

    status_msg = await query.message.reply_text("🐙 <i>Syncing backup branch to GitHub remote...</i>", parse_mode=ParseMode.HTML)
    proc = subprocess.run([str(TRANSPORT_SCRIPT), "sync"], capture_output=True, text=True)
    out = proc.stdout + "\n" + proc.stderr

    if proc.returncode == 0:
        await status_msg.edit_text(
            f"✅ <b>GitHub Sync Complete!</b>\n\n<pre>{escape(out[:2000])}</pre>",
            reply_markup=main_menu_keyboard(),
            parse_mode=ParseMode.HTML
        )
    else:
        await status_msg.edit_text(
            f"❌ <b>GitHub Sync Failed:</b>\n\n<pre>{escape(out[:2000])}</pre>",
            reply_markup=main_menu_keyboard(),
            parse_mode=ParseMode.HTML
        )
