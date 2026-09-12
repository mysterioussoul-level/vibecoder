"""
Main Telegram Bot Application entry point for VibeCoder.
Wires up all command handlers, inline callbacks, and execution loops.
"""

import sys
import logging
import asyncio
import time
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from vibecoder.telegram_bot.handlers import start, engines, projects, git_menu, shell_cmd, backup, vibe, auth
from vibecoder.config import TELEGRAM_BOT_TOKEN, OWNER_ID

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("VibeCoderBot")

async def on_startup(app: Application):
    """Notify owner when bot starts or recovers from a crash/reboot."""
    logger.info("VibeCoder Bot initialized and ready.")
    if OWNER_ID:
        try:
            from vibecoder.config import CODESPACE_NAME, settings
            from vibecoder.core.project_manager import project_manager
            from vibecoder.telegram_bot.ui.formatters import escape
            proj = project_manager.get_active_project()
            eng = settings.get("default_engine", "antigravity")
            text = (
                "🚀 <b>VibeCoder Online!</b>\n"
                "─────────────────────────────\n"
                f"🛰 <b>Codespace:</b> <code>{escape(CODESPACE_NAME)}</code> 🟢\n"
                f"📂 <b>Active Project:</b> <code>{escape(proj['name'])}</code>\n"
                f"🤖 <b>AI Engine:</b> <b>{escape(eng)}</b>\n"
                "⏱ <b>Status:</b> System recovered &amp; listening for commands!\n"
                "─────────────────────────────\n"
                "💡 <i>Send any message or prompt to vibe code autonomously!</i>"
            )
            await app.bot.send_message(
                chat_id=OWNER_ID,
                text=text,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.warning(f"Could not send startup notification: {e}")

async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Handle unexpected errors without terminating the bot application."""
    logger.error("Exception while handling an update:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            from vibecoder.telegram_bot.ui.formatters import escape
            err_msg = str(context.error)
            if len(err_msg) > 200:
                err_msg = err_msg[:200] + "..."
            await update.effective_message.reply_text(
                f"⚠️ <b>Recovered from unexpected error:</b>\n<code>{escape(err_msg)}</code>\n\n"
                "<i>Your workspace state and project files are safe. Tap /start to reload dashboard.</i>",
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass

def build_application(token: str) -> Application:
    app = Application.builder().token(token).post_init(on_startup).build()
    app.add_error_handler(global_error_handler)

    # Commands
    app.add_handler(CommandHandler(["start", "menu"], start.start_handler))
    app.add_handler(CommandHandler("help", start.help_handler))
    app.add_handler(CommandHandler(["engine", "engines"], engines.engines_menu_handler))
    app.add_handler(CommandHandler(["projects", "project", "switch"], projects.projects_menu_handler))
    app.add_handler(CommandHandler("clone", projects.clone_command))
    app.add_handler(CommandHandler("new", projects.new_command))
    app.add_handler(CommandHandler(["git", "status"], git_menu.git_menu_handler))
    app.add_handler(CommandHandler("diff", git_menu.view_diff_handler))
    app.add_handler(CommandHandler("commit", git_menu.commit_handler))
    app.add_handler(CommandHandler("push", git_menu.push_handler))
    app.add_handler(CommandHandler(["pull", "git_pull"], git_menu.pull_handler))
    app.add_handler(CommandHandler(["publish", "github_publish"], git_menu.publish_handler))
    app.add_handler(CommandHandler(["sync", "update"], git_menu.sync_workspace_handler))
    app.add_handler(CommandHandler("revert", git_menu.revert_confirm_handler))
    app.add_handler(CommandHandler(["test", "tests"], shell_cmd.run_tests_handler))
    app.add_handler(CommandHandler(["sh", "terminal"], shell_cmd.shell_command_handler))
    app.add_handler(CommandHandler(["backup", "transport", "export"], backup.backup_menu_handler))
    app.add_handler(CommandHandler(["auth", "login"], auth.auth_command))

    # Callback Query Handlers
    app.add_handler(CallbackQueryHandler(start.dashboard_callback, pattern="^menu_dashboard$"))
    app.add_handler(CallbackQueryHandler(start.help_handler, pattern="^vibe_help$"))
    
    # Engine Callbacks
    app.add_handler(CallbackQueryHandler(engines.engines_menu_handler, pattern="^menu_engines$"))
    app.add_handler(CallbackQueryHandler(engines.set_engine_callback, pattern="^set_engine:"))

    # Project Callbacks
    app.add_handler(CallbackQueryHandler(projects.projects_menu_handler, pattern="^menu_projects$"))
    app.add_handler(CallbackQueryHandler(projects.select_project_callback, pattern="^select_proj:"))
    app.add_handler(CallbackQueryHandler(projects.new_project_menu, pattern="^menu_new_project$"))
    app.add_handler(CallbackQueryHandler(projects.template_chosen_callback, pattern="^new_tmpl:"))
    app.add_handler(CallbackQueryHandler(projects.clone_repo_prompt, pattern="^menu_clone_repo$"))

    # Git Callbacks
    app.add_handler(CallbackQueryHandler(git_menu.git_menu_handler, pattern="^menu_git$"))
    app.add_handler(CallbackQueryHandler(git_menu.view_diff_handler, pattern="^git_view_diff$"))
    app.add_handler(CallbackQueryHandler(git_menu.commit_handler, pattern="^git_commit_quick$"))
    app.add_handler(CallbackQueryHandler(git_menu.pull_handler, pattern="^git_pull$"))
    app.add_handler(CallbackQueryHandler(git_menu.push_handler, pattern="^git_push$"))
    app.add_handler(CallbackQueryHandler(git_menu.publish_handler, pattern="^git_publish$"))
    app.add_handler(CallbackQueryHandler(git_menu.revert_confirm_handler, pattern="^git_revert_confirm$"))
    app.add_handler(CallbackQueryHandler(git_menu.do_revert_handler, pattern="^git_do_revert$"))

    # Shell & Test Callbacks
    app.add_handler(CallbackQueryHandler(shell_cmd.shell_menu_prompt, pattern="^menu_shell$"))
    app.add_handler(CallbackQueryHandler(shell_cmd.run_tests_handler, pattern="^action_run_tests$"))

    # Backup Callbacks
    app.add_handler(CallbackQueryHandler(backup.backup_menu_handler, pattern="^menu_backup$"))
    app.add_handler(CallbackQueryHandler(backup.send_backup_document_callback, pattern="^backup_send_doc$"))
    app.add_handler(CallbackQueryHandler(backup.export_cloud_link_callback, pattern="^backup_cloud_link$"))
    app.add_handler(CallbackQueryHandler(backup.sync_github_callback, pattern="^backup_sync_git$"))

    # Auth & Credential Callbacks
    app.add_handler(CallbackQueryHandler(auth.auth_menu_handler, pattern="^menu_auth$"))
    app.add_handler(CallbackQueryHandler(auth.auth_copilot_device_callback, pattern="^auth_copilot_device$"))
    app.add_handler(CallbackQueryHandler(auth.auth_copilot_token_prompt_callback, pattern="^auth_copilot_token_prompt$"))
    app.add_handler(CallbackQueryHandler(auth.auth_gemini_prompt_callback, pattern="^auth_gemini_prompt$"))
    app.add_handler(CallbackQueryHandler(auth.auth_openrouter_prompt_callback, pattern="^auth_openrouter_prompt$"))

    # Document upload handler (e.g. antigravity-oauth-token files or project files)
    app.add_handler(MessageHandler(filters.Document.ALL, vibe.vibe_document_handler))

    # Natural language vibe prompt handler (all non-command text messages)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, vibe.vibe_message_handler))

    return app

def main():
    token = TELEGRAM_BOT_TOKEN
    if not token:
        print("[ERROR] No Telegram Bot Token found. Please configure VIBE_BOT_TOKEN or BOT_TOKEN in .env or run ./set_vibe_token.sh <token>")
        sys.exit(1)

    print("=" * 60)
    print("🚀 VIBECODER • AUTONOMOUS STUDIO TELEGRAM BOT STARTING")
    print(f"Owner ID: {OWNER_ID or '[Any / Unrestricted]'}")
    print("=" * 60)

    consecutive_failures = 0
    while True:
        try:
            app = build_application(token)
            consecutive_failures = 0
            app.run_polling(drop_pending_updates=True)
            break
        except KeyboardInterrupt:
            logger.info("Bot manually terminated by user.")
            break
        except Exception as e:
            consecutive_failures += 1
            wait_sec = min(2 ** consecutive_failures, 30)
            logger.error(f"Telegram polling crashed with: {e}. Auto-recovering in {wait_sec}s...", exc_info=True)
            time.sleep(wait_sec)

if __name__ == "__main__":
    main()
