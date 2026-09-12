"""
Project management and switching handlers for VibeCoder Telegram Bot.
"""

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from vibecoder.core.project_manager import project_manager, TEMPLATES
from vibecoder.core import git_ops
from vibecoder.telegram_bot.ui.keyboards import (
    project_selection_keyboard,
    template_selection_keyboard,
    main_menu_keyboard
)
from vibecoder.telegram_bot.ui.formatters import escape
from vibecoder.telegram_bot.handlers.start import is_authorized

async def projects_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        return

    projects = project_manager.list_projects()
    active = project_manager.get_active_project()

    text = (
        "📂 <b>Workspace Projects</b>\n"
        "─────────────────────────────\n"
        f"Active: <b>{escape(active['name'])}</b> (<code>{escape(active['branch'])}</code>)\n\n"
        "Select a project below to switch active workspace, or create/clone a new one:"
    )

    markup = project_selection_keyboard(projects)
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)

async def select_project_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_authorized(query.from_user.id):
        return

    idx = int(query.data.split(":", 1)[1])
    projects = project_manager.list_projects()
    if 0 <= idx < len(projects):
        target = projects[idx]
        project_manager.set_active_project(target["path"])
        await query.answer(f"Switched to {target['name']}!", show_alert=True)

    projects = project_manager.list_projects()
    active = project_manager.get_active_project()
    text = (
        "📂 <b>Workspace Projects</b>\n"
        "─────────────────────────────\n"
        f"✅ Active Project: <b>{escape(active['name'])}</b>\n"
        f"Branch: <code>{escape(active['branch'])}</code>\n"
        f"Path: <code>{escape(active['path'])}</code>\n\n"
        "Select another project or return to Dashboard:"
    )
    markup = project_selection_keyboard(projects)
    await query.edit_message_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)

async def new_project_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "➕ <b>Create New Project</b>\n"
            "─────────────────────────────\n"
            "Choose a starter template for your new project:\n\n"
            "• <b>Python FastAPI:</b> Modern REST API with automatic pytest suite\n"
            "• <b>Python CLI:</b> Command line utility with argparse and tests\n"
            "• <b>Node Express:</b> Express.js web server\n"
            "• <b>Modern Web:</b> HTML5, CSS3, & modern vanilla JS\n"
            "• <b>Blank:</b> Clean empty repo with Git initialized",
            reply_markup=template_selection_keyboard(),
            parse_mode=ParseMode.HTML
        )

async def template_chosen_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_authorized(query.from_user.id):
        return

    tmpl = query.data.split(":", 1)[1]
    context.user_data["pending_action"] = "new_project_name"
    context.user_data["selected_template"] = tmpl

    await query.edit_message_text(
        f"➕ <b>Create {escape(tmpl.capitalize())} Project</b>\n"
        "─────────────────────────────\n"
        "Please send the <b>Name</b> of your new project as a text message:\n"
        "<i>(e.g., <code>my-cool-api</code> or <code>vibe-demo</code>)</i>",
        parse_mode=ParseMode.HTML
    )

async def clone_repo_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        context.user_data["pending_action"] = "clone_repo_url"
        await query.edit_message_text(
            "🔗 <b>Clone GitHub Repository</b>\n"
            "─────────────────────────────\n"
            "Send the GitHub repository URL to clone:\n\n"
            "<i>Example:</i>\n"
            "<code>https://github.com/fastapi/fastapi</code>\n"
            "<code>https://github.com/tiangolo/full-stack-fastapi-template.git</code>",
            parse_mode=ParseMode.HTML
        )

async def clone_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        return

    if not context.args:
        await update.message.reply_text("Usage: <code>/clone &lt;repo_url&gt; [optional_name]</code>", parse_mode=ParseMode.HTML)
        return

    url = context.args[0]
    custom_name = context.args[1] if len(context.args) > 1 else None

    status_msg = await update.message.reply_text(f"⏳ Cloning repository <code>{escape(url)}</code>...", parse_mode=ParseMode.HTML)
    success, msg, path = project_manager.clone_repo(url, custom_name)

    if success:
        await status_msg.edit_text(
            f"✅ <b>Repository Cloned!</b>\n\n{escape(msg)}\nPath: <code>{escape(path)}</code>\n\nReady for vibe coding!",
            reply_markup=main_menu_keyboard(),
            parse_mode=ParseMode.HTML
        )
    else:
        await status_msg.edit_text(f"❌ <b>Clone Failed</b>\n\n{escape(msg)}", parse_mode=ParseMode.HTML)

async def new_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        return

    if not context.args:
        await update.message.reply_text("Usage: <code>/new &lt;project_name&gt; [template: python|cli|node|web|blank]</code>", parse_mode=ParseMode.HTML)
        return

    name = context.args[0]
    tmpl = context.args[1] if len(context.args) > 1 else "python"

    success, msg, path = project_manager.create_project(name, tmpl)
    if success:
        await update.message.reply_text(
            f"✅ <b>Project Created!</b>\n\n{escape(msg)}\nPath: <code>{escape(path)}</code>",
            reply_markup=main_menu_keyboard(),
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(f"❌ <b>Creation Failed</b>: {escape(msg)}", parse_mode=ParseMode.HTML)
