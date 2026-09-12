"""
AI Engine switcher handlers for VibeCoder Telegram Bot.
"""

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from vibecoder.config import settings
from vibecoder.core.engine_manager import engine_manager
from vibecoder.telegram_bot.ui.keyboards import engine_selection_keyboard, main_menu_keyboard
from vibecoder.telegram_bot.handlers.start import is_authorized

async def engines_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        return

    engines = engine_manager.list_engines()
    text = (
        "🤖 <b>Select Active AI Engine</b>\n"
        "─────────────────────────────\n"
        "Choose which engine executes your vibe coding requests:\n\n"
        "• <b>Antigravity:</b> Gemini 3.8 Flash High with 1M context & full tool capability.\n"
        "• <b>Aider:</b> OpenRouter powered precision code & diff editor.\n"
        "• <b>Copilot:</b> GitHub Copilot CLI (Student plan / Auto dynamic).\n"
        "• <b>Auto Vibe:</b> Self-healing ensemble (Plan + Code + Test + Auto-heal)."
    )

    markup = engine_selection_keyboard(engines)
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)

async def set_engine_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_authorized(query.from_user.id):
        return

    engine_id = query.data.split(":", 1)[1]
    if engine_manager.set_default_engine(engine_id):
        engine = engine_manager.get_engine(engine_id)
        await query.answer(f"Switched to {engine.name}!", show_alert=True)

    engines = engine_manager.list_engines()
    markup = engine_selection_keyboard(engines)
    text = (
        "🤖 <b>Select Active AI Engine</b>\n"
        "─────────────────────────────\n"
        f"✅ Active Engine set to: <b>{engine_manager.get_engine().description}</b>\n\n"
        "Tap below to switch anytime:"
    )
    await query.edit_message_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)
