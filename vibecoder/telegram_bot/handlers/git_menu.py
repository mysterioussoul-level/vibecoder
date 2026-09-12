"""
Git control handlers for VibeCoder Telegram Bot.
Provides diff viewing, commit, push, and rollback.
"""

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from vibecoder.config import settings
from vibecoder.core.project_manager import project_manager
from vibecoder.core import git_ops
from vibecoder.telegram_bot.ui.keyboards import git_menu_keyboard, confirm_revert_keyboard, main_menu_keyboard
from vibecoder.telegram_bot.ui.formatters import escape, format_diff_view
from vibecoder.telegram_bot.handlers.start import is_authorized

async def git_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        return

    proj = project_manager.get_active_project()
    git_st = git_ops.get_status(proj["path"])
    remote_url = git_ops.get_remote_url(proj["path"]) or "None (Local only)"

    parts = [
        f"📊 <b>Git Status • {escape(proj['name'])}</b>\n"
        "─────────────────────────────\n"
        f"Branch: <code>{escape(git_st['branch'])}</code>\n"
        f"Remote: <code>{escape(remote_url)}</code>\n"
        f"Status: {escape(git_st['summary'])}\n"
    ]

    if git_st["modified"]:
        parts.append("<b>Modified:</b>\n" + "\n".join(f"• <code>{escape(f)}</code>" for f in git_st["modified"][:10]))
    if git_st["untracked"]:
        parts.append("<b>Untracked:</b>\n" + "\n".join(f"+ <code>{escape(f)}</code>" for f in git_st["untracked"][:10]))
    if git_st["staged"]:
        parts.append("<b>Staged:</b>\n" + "\n".join(f"✓ <code>{escape(f)}</code>" for f in git_st["staged"][:10]))

    text = "\n\n".join(parts)
    markup = git_menu_keyboard(has_changes=not git_st["clean"])

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)

async def view_diff_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        return

    proj = project_manager.get_active_project()
    diff_text = git_ops.get_diff(proj["path"])
    msg = format_diff_view(diff_text, proj["name"])

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(msg, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

async def commit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        return

    proj = project_manager.get_active_project()
    msg = " ".join(context.args) if (context and context.args) else f"Update via VibeCoder on {proj['name']}"

    success, out = git_ops.commit_all(proj["path"], msg)
    if success:
        text = f"✅ <b>Committed Successfully!</b>\n\n<code>{escape(out)}</code>"
    else:
        text = f"❌ <b>Commit Failed:</b>\n\n<code>{escape(out)}</code>"

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(text, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def push_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        return

    proj = project_manager.get_active_project()
    status_msg = None
    if update.callback_query:
        await update.callback_query.answer()
        status_msg = await update.callback_query.message.reply_text("⏳ Pushing commits to remote GitHub repository...", parse_mode=ParseMode.HTML)
    else:
        status_msg = await update.message.reply_text("⏳ Pushing commits to remote GitHub repository...", parse_mode=ParseMode.HTML)

    success, out = git_ops.push(proj["path"])
    if success:
        await status_msg.edit_text(f"🚀 <b>Git Push Succeeded!</b>\n\n<code>{escape(out)}</code>", parse_mode=ParseMode.HTML)
    else:
        await status_msg.edit_text(f"❌ <b>Git Push Failed:</b>\n\n<code>{escape(out)}</code>", parse_mode=ParseMode.HTML)

async def revert_confirm_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "⚠️ <b>Confirm Revert</b>\n\n"
            "This will hard-reset all unstaged and staged changes in the active project back to the latest commit.\n"
            "Are you sure?",
            reply_markup=confirm_revert_keyboard(),
            parse_mode=ParseMode.HTML
        )

async def do_revert_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        proj = project_manager.get_active_project()
        success, out = git_ops.revert_all(proj["path"])
        if success:
            await query.edit_message_text(
                f"⏪ <b>Working Directory Reverted!</b>\n\n{escape(out)}",
                reply_markup=main_menu_keyboard(),
                parse_mode=ParseMode.HTML
            )
        else:
            await query.edit_message_text(
                f"❌ <b>Revert Failed:</b>\n\n{escape(out)}",
                reply_markup=main_menu_keyboard(),
                parse_mode=ParseMode.HTML
            )

async def pull_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pull latest updates from GitHub remote into active project."""
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        return

    proj = project_manager.get_active_project()
    status_msg = None
    if update.callback_query:
        await update.callback_query.answer()
        status_msg = await update.callback_query.message.reply_text("⏳ Pulling latest updates from GitHub...", parse_mode=ParseMode.HTML)
    else:
        status_msg = await update.message.reply_text("⏳ Pulling latest updates from GitHub...", parse_mode=ParseMode.HTML)

    success, out = git_ops.pull(proj["path"])
    if success:
        await status_msg.edit_text(f"⬇️ <b>Git Pull Succeeded!</b>\n\n<code>{escape(out)}</code>", parse_mode=ParseMode.HTML)
    else:
        await status_msg.edit_text(f"❌ <b>Git Pull Failed:</b>\n\n<code>{escape(out)}</code>", parse_mode=ParseMode.HTML)

async def publish_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Publish the active project as a GitHub repository using gh CLI."""
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        return

    proj = project_manager.get_active_project()
    repo_name = context.args[0] if (context and context.args) else proj["name"]

    status_msg = None
    if update.callback_query:
        await update.callback_query.answer()
        status_msg = await update.callback_query.message.reply_text(
            f"⏳ Publishing <code>{escape(repo_name)}</code> to GitHub via GitHub CLI...",
            parse_mode=ParseMode.HTML
        )
    else:
        status_msg = await update.message.reply_text(
            f"⏳ Publishing <code>{escape(repo_name)}</code> to GitHub via GitHub CLI...",
            parse_mode=ParseMode.HTML
        )

    success, out = git_ops.publish_to_github(proj["path"], repo_name=repo_name, private=True)
    if success:
        await status_msg.edit_text(f"🐙 <b>GitHub Repository Ready!</b>\n\n{escape(out)}", parse_mode=ParseMode.HTML)
    else:
        await status_msg.edit_text(f"❌ <b>GitHub Creation Failed:</b>\n\n<code>{escape(out)}</code>", parse_mode=ParseMode.HTML)

async def sync_workspace_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pull latest updates for the VibeCoder system and workspace itself from GitHub."""
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        return

    from vibecoder.config import WORKSPACE_ROOT
    status_msg = await update.message.reply_text("⏳ Updating VibeCoder workspace from GitHub origin...", parse_mode=ParseMode.HTML)
    success, out = git_ops.pull(str(WORKSPACE_ROOT))
    if success:
        await status_msg.edit_text(f"🔄 <b>Workspace Updated!</b>\n\n<code>{escape(out)}</code>", parse_mode=ParseMode.HTML)
    else:
        await status_msg.edit_text(f"❌ <b>Workspace Update Failed:</b>\n\n<code>{escape(out)}</code>", parse_mode=ParseMode.HTML)
