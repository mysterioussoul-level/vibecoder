"""
Start, Help, and Dashboard handlers for VibeCoder Telegram Bot.
"""

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from vibecoder.config import OWNER_ID, settings
from vibecoder.core.project_manager import project_manager
from vibecoder.core.engine_manager import engine_manager
from vibecoder.core import git_ops
from vibecoder.telegram_bot.ui.keyboards import main_menu_keyboard
from vibecoder.telegram_bot.ui.formatters import format_dashboard

def is_authorized(user_id: int) -> bool:
    if not OWNER_ID:
        return True
    return user_id == OWNER_ID

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_authorized(user.id):
        await update.message.reply_text(
            f"⛔ <b>Access Restricted</b>\nYour User ID (<code>{user.id}</code>) is not authorized.",
            parse_mode=ParseMode.HTML
        )
        return

    proj = project_manager.get_active_project()
    engine = engine_manager.get_engine()
    git_st = git_ops.get_status(proj["path"])

    text = format_dashboard(proj, engine.description, git_st)
    await update.message.reply_text(
        text,
        reply_markup=main_menu_keyboard(),
        parse_mode=ParseMode.HTML
    )

async def dashboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_authorized(query.from_user.id):
        return

    proj = project_manager.get_active_project()
    engine = engine_manager.get_engine()
    git_st = git_ops.get_status(proj["path"])

    text = format_dashboard(proj, engine.description, git_st)
    await query.edit_message_text(
        text,
        reply_markup=main_menu_keyboard(),
        parse_mode=ParseMode.HTML
    )

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "💡 <b>𝗩𝗜𝗕𝗘 𝗖𝗢𝗗𝗘𝗥 • 𝗤𝘂𝗶𝗰𝗸 𝗚𝘂𝗶𝗱𝗲</b>\n\n"
        "Just send a text message describing what you want to build or change!\n\n"
        "<b>Commands:</b>\n"
        "• /start or /menu - Main Dashboard\n"
        "• /engine - Switch AI coding engine\n"
        "• /projects - Manage & switch projects\n"
        "• /clone &lt;url&gt; - Clone a GitHub repository\n"
        "• /new &lt;name&gt; - Scaffold a new project\n"
        "• /diff - View working tree git diff\n"
        "• /commit [message] - Commit all changes\n"
        "• /push - Push commits to GitHub\n"
        "• /test - Run automated tests or syntax verification\n"
        "• /sh &lt;command&gt; - Execute shell command in project directory\n"
        "• /backup - Export complete workspace backup & transport to new Codespace"
    )
    if update.message:
        await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(help_text, parse_mode=ParseMode.HTML)
