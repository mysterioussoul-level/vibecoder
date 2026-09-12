"""
Authentication & Credential lifecycle handlers for VibeCoder Telegram Bot.
Supports interactive OAuth device flow, direct token pasting, and credential status inspection.
"""

import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from vibecoder.core.auth_manager import auth_manager
from vibecoder.telegram_bot.ui.keyboards import (
    auth_menu_keyboard,
    copilot_device_keyboard,
    main_menu_keyboard
)
from vibecoder.telegram_bot.ui.formatters import escape, format_auth_status
from vibecoder.telegram_bot.handlers.start import is_authorized

async def auth_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        return

    status_msg = None
    if update.callback_query:
        await update.callback_query.answer()
        status_msg = await update.callback_query.message.reply_text(
            "🔍 <i>Checking credentials and connectivity for all AI engines...</i>",
            parse_mode=ParseMode.HTML
        )
    else:
        status_msg = await update.message.reply_text(
            "🔍 <i>Checking credentials and connectivity for all AI engines...</i>",
            parse_mode=ParseMode.HTML
        )

    statuses = await auth_manager.check_all_status()
    text = format_auth_status(statuses)
    markup = auth_menu_keyboard()

    await status_msg.edit_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)

async def auth_copilot_device_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_authorized(query.from_user.id):
        return

    status_msg = await query.message.reply_text(
        "⏳ <i>Requesting GitHub Device Code for Copilot login...</i>",
        parse_mode=ParseMode.HTML
    )

    ok, url, code, proc = await auth_manager.start_copilot_device_login()
    if not ok:
        await status_msg.edit_text(
            f"❌ <b>Device Login Failed:</b>\n{escape(code)}",
            reply_markup=auth_menu_keyboard(),
            parse_mode=ParseMode.HTML
        )
        return

    login_card = (
        "🔐 <b>GitHub Copilot Authentication</b>\n"
        "─────────────────────────────\n"
        "To authorize or switch your Copilot account:\n\n"
        "1. Click the button below to open GitHub\n"
        f"2. Enter this one-time code: <code>{code}</code>\n"
        "3. Click <b>Continue</b> and approve access\n\n"
        "⏳ <i>Waiting for approval... This message will automatically update once confirmed!</i>"
    )

    markup = copilot_device_keyboard(url)
    await status_msg.edit_text(login_card, reply_markup=markup, parse_mode=ParseMode.HTML)

    async def poll_completion():
        try:
            returncode = await proc.wait()
            if returncode == 0:
                await status_msg.edit_text(
                    "✅ <b>GitHub Copilot Login Successful!</b>\n\n"
                    "Your GitHub Copilot account has been authorized and is active for vibe coding.",
                    reply_markup=auth_menu_keyboard(),
                    parse_mode=ParseMode.HTML
                )
            else:
                await status_msg.edit_text(
                    "❌ <b>Copilot Login Expired or Cancelled</b>\n"
                    "Please tap below to try again.",
                    reply_markup=auth_menu_keyboard(),
                    parse_mode=ParseMode.HTML
                )
        except Exception:
            pass

    asyncio.create_task(poll_completion())

async def auth_copilot_token_prompt_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_authorized(query.from_user.id):
        return

    context.user_data["pending_action"] = "set_copilot_token"
    await query.edit_message_text(
        "🐙 <b>Enter GitHub Copilot Token</b>\n"
        "─────────────────────────────\n"
        "Please send your GitHub Personal Access Token (PAT) or Copilot token as a message.\n\n"
        "<i>Tokens are stored securely in local credentials and .env.vibe.</i>",
        parse_mode=ParseMode.HTML
    )

async def auth_gemini_prompt_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_authorized(query.from_user.id):
        return

    context.user_data["pending_action"] = "set_gemini_auth"
    await query.edit_message_text(
        "🧠 <b>Replace Gemini 3.8 / Antigravity Credentials</b>\n"
        "─────────────────────────────\n"
        "Choose an option to replace your Gemini credentials:\n\n"
        "1. <b>Send API Key:</b> Send your Google AI Studio key (starts with <code>AIza...</code>)\n"
        "2. <b>Send JSON Token:</b> Paste the JSON contents of your <code>antigravity-oauth-token</code>\n"
        "3. <b>Upload File:</b> Simply upload the <code>antigravity-oauth-token</code> file as a document into this chat!\n\n"
        "Send your key or JSON payload as a reply now:",
        parse_mode=ParseMode.HTML
    )

async def auth_openrouter_prompt_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_authorized(query.from_user.id):
        return

    context.user_data["pending_action"] = "set_openrouter_key"
    await query.edit_message_text(
        "⚡ <b>Replace OpenRouter API Key</b>\n"
        "─────────────────────────────\n"
        "Send your OpenRouter API Key (starts with <code>sk-or-v1-...</code>):\n\n"
        "<i>Get a key or view credits at openrouter.ai/keys</i>",
        parse_mode=ParseMode.HTML
    )

async def auth_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        return

    if not context.args:
        await auth_menu_handler(update, context)
        return

    sub = context.args[0].lower()
    val = context.args[1] if len(context.args) > 1 else ""

    if sub == "copilot" and val:
        ok, msg = await auth_manager.set_copilot_token(val)
        icon = "✅" if ok else "❌"
        await update.message.reply_text(f"{icon} {escape(msg)}", parse_mode=ParseMode.HTML)
    elif sub == "gemini" and val:
        ok, msg = await auth_manager.set_gemini_auth(val)
        icon = "✅" if ok else "❌"
        await update.message.reply_text(f"{icon} {escape(msg)}", parse_mode=ParseMode.HTML)
    elif sub in ("openrouter", "aider") and val:
        ok, msg = await auth_manager.set_openrouter_key(val)
        icon = "✅" if ok else "❌"
        await update.message.reply_text(f"{icon} {escape(msg)}", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(
            "Usage:\n"
            "• <code>/auth</code> - Open Auth Control Center\n"
            "• <code>/auth copilot &lt;token&gt;</code> - Apply Copilot token\n"
            "• <code>/auth gemini &lt;token_or_key&gt;</code> - Apply Gemini credentials\n"
            "• <code>/auth openrouter &lt;key&gt;</code> - Apply OpenRouter key",
            parse_mode=ParseMode.HTML
        )
