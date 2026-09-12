"""
Shell terminal command execution and test runners for VibeCoder Telegram Bot.
"""

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from vibecoder.core.project_manager import project_manager
from vibecoder.core.shell_runner import execute_shell
from vibecoder.core import test_runner
from vibecoder.telegram_bot.ui.formatters import escape, format_test_report_view
from vibecoder.telegram_bot.ui.keyboards import main_menu_keyboard
from vibecoder.telegram_bot.handlers.start import is_authorized

async def shell_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        return

    if not context.args:
        await update.message.reply_text(
            "💻 <b>Shell Command Runner</b>\n\n"
            "Usage: <code>/sh &lt;bash command&gt;</code>\n"
            "<i>Commands execute inside the active project directory.</i>\n\n"
            "<i>Examples:</i>\n"
            "• <code>/sh ls -la</code>\n"
            "• <code>/sh pip install requests</code>\n"
            "• <code>/sh pytest -v</code>\n"
            "• <code>/sh npm run build</code>",
            parse_mode=ParseMode.HTML
        )
        return

    cmd = " ".join(context.args)
    proj = project_manager.get_active_project()

    status_msg = await update.message.reply_text(
        f"⚡ <i>Executing in</i> <code>{escape(proj['name'])}</code>:\n<code>$ {escape(cmd)}</code>",
        parse_mode=ParseMode.HTML
    )

    code, out, dur = await execute_shell(cmd, cwd=proj["path"], timeout=120)
    icon = "✅" if code == 0 else "❌"

    if len(out) > 3500:
        out = out[:3500] + "\n... [Truncated for Telegram]"

    response_text = (
        f"{icon} <b>Exit Code:</b> {code} ({dur}s)\n"
        f"<b>Directory:</b> <code>{escape(proj['path'])}</code>\n"
        f"<b>Command:</b> <code>$ {escape(cmd)}</code>\n"
        "─────────────────────────────\n"
        f"<pre>{escape(out or '[No output]')}</pre>"
    )

    await status_msg.edit_text(response_text, parse_mode=ParseMode.HTML)

async def run_tests_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        return

    proj = project_manager.get_active_project()

    status_msg = None
    if update.callback_query:
        await update.callback_query.answer()
        status_msg = await update.callback_query.message.reply_text(
            f"🧪 <i>Running automated tests for</i> <code>{escape(proj['name'])}</code>...",
            parse_mode=ParseMode.HTML
        )
    else:
        status_msg = await update.message.reply_text(
            f"🧪 <i>Running automated tests for</i> <code>{escape(proj['name'])}</code>...",
            parse_mode=ParseMode.HTML
        )

    report = test_runner.run_project_tests(proj["path"])
    msg = format_test_report_view(report, proj["name"])

    await status_msg.edit_text(msg, reply_markup=main_menu_keyboard(), parse_mode=ParseMode.HTML)

async def shell_menu_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        proj = project_manager.get_active_project()
        await query.edit_message_text(
            "💻 <b>Terminal Shell Runner</b>\n"
            "─────────────────────────────\n"
            f"Active Directory: <code>{escape(proj['path'])}</code>\n\n"
            "Send any shell command using <code>/sh &lt;command&gt;</code>\n\n"
            "<i>Examples:</i>\n"
            "• <code>/sh pip install &lt;package&gt;</code>\n"
            "• <code>/sh npm test</code>\n"
            "• <code>/sh cat main.py</code>\n"
            "• <code>/sh git log -n 3</code>",
            reply_markup=main_menu_keyboard(),
            parse_mode=ParseMode.HTML
        )
