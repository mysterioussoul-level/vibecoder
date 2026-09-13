"""
Vibe Coding prompt processor for VibeCoder Telegram Bot.
Transforms natural language vibes into autonomous code generation, diffing, and testing.
"""

import asyncio
import time
import logging
from collections import deque
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction

logger = logging.getLogger("VibeHandler")

from vibecoder.config import settings
from vibecoder.core.project_manager import project_manager
from vibecoder.core.engine_manager import engine_manager
from vibecoder.telegram_bot.ui.formatters import escape, format_vibe_result
from vibecoder.telegram_bot.ui.keyboards import vibe_result_keyboard, main_menu_keyboard
from vibecoder.telegram_bot.handlers.start import is_authorized

async def vibe_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        return

    text = update.message.text.strip()
    if not text:
        return

    pending = context.user_data.get("pending_action")
    if pending == "new_project_name":
        context.user_data["pending_action"] = None
        tmpl = context.user_data.get("selected_template", "python")
        success, msg, path = project_manager.create_project(text, tmpl)
        if success:
            await update.message.reply_text(
                f"✅ <b>Project Created!</b>\n\n{escape(msg)}\nPath: <code>{escape(path)}</code>\n\nReady for vibe coding!",
                reply_markup=main_menu_keyboard(),
                parse_mode=ParseMode.HTML
            )
        else:
            await update.message.reply_text(f"❌ <b>Creation Failed:</b> {escape(msg)}", parse_mode=ParseMode.HTML)
        return

    elif pending == "clone_repo_url":
        context.user_data["pending_action"] = None
        status_msg = await update.message.reply_text(f"⏳ Cloning repository <code>{escape(text)}</code>...", parse_mode=ParseMode.HTML)
        success, msg, path = project_manager.clone_repo(text)
        if success:
            await status_msg.edit_text(
                f"✅ <b>Repository Cloned!</b>\n\n{escape(msg)}\nPath: <code>{escape(path)}</code>\n\nReady for vibe coding!",
                reply_markup=main_menu_keyboard(),
                parse_mode=ParseMode.HTML
            )
        else:
            await status_msg.edit_text(f"❌ <b>Clone Failed:</b> {escape(msg)}", parse_mode=ParseMode.HTML)
        return

    elif pending == "set_copilot_token":
        context.user_data["pending_action"] = None
        status_msg = await update.message.reply_text("⏳ Verifying Copilot token...", parse_mode=ParseMode.HTML)
        from vibecoder.core.auth_manager import auth_manager
        ok, msg = await auth_manager.set_copilot_token(text)
        icon = "✅" if ok else "❌"
        await status_msg.edit_text(f"{icon} <b>Copilot Auth:</b> {escape(msg)}", reply_markup=main_menu_keyboard(), parse_mode=ParseMode.HTML)
        return

    elif pending == "set_gemini_auth":
        context.user_data["pending_action"] = None
        status_msg = await update.message.reply_text("⏳ Applying and validating Gemini credentials...", parse_mode=ParseMode.HTML)
        from vibecoder.core.auth_manager import auth_manager
        ok, msg = await auth_manager.set_gemini_auth(text)
        icon = "✅" if ok else "❌"
        await status_msg.edit_text(f"{icon} <b>Gemini Auth:</b> {escape(msg)}", reply_markup=main_menu_keyboard(), parse_mode=ParseMode.HTML)
        return

    elif pending == "set_openrouter_key":
        context.user_data["pending_action"] = None
        status_msg = await update.message.reply_text("⏳ Testing OpenRouter API key...", parse_mode=ParseMode.HTML)
        from vibecoder.core.auth_manager import auth_manager
        ok, msg = await auth_manager.set_openrouter_key(text)
        icon = "✅" if ok else "❌"
        await status_msg.edit_text(f"{icon} <b>OpenRouter:</b> {escape(msg)}", reply_markup=main_menu_keyboard(), parse_mode=ParseMode.HTML)
        return

    proj = project_manager.get_active_project()
    engine = engine_manager.get_engine()

    # Determine active model display name
    eng_key = engine.name.lower()
    if eng_key == "antigravity":
        m = settings.get("agy_model", "gemini-3.8-flash-medium")
        model_display = "Gemini 3.8 Flash" if "gemini-3.8-flash" in m else m
    elif eng_key == "ensemble":
        model_display = "Gemini 3.8 Flash (Auto Vibe)"
    elif eng_key == "copilot":
        model_display = "GitHub Copilot"
    elif eng_key == "aider":
        model_display = "Aider (OpenRouter)"
    else:
        model_display = engine.name.capitalize()

    start_time = time.time()
    current_stage = "Inspecting workspace files & dependencies..."
    spinners = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    recent_commands = deque(maxlen=5)
    recent_commands.append(f"$ cd {proj['name']}")
    recent_commands.append("• Initializing workspace analysis...")

    def format_status_card(spinner: str, elapsed: int) -> str:
        mins, secs = divmod(elapsed, 60)
        time_str = f"{mins:02d}:{secs:02d}"
        cmds_str = "\n".join(recent_commands) if recent_commands else "• Waiting for activity..."
        return (
            "⚡ <b>𝗩𝗜𝗕𝗘 𝗖𝗢𝗗𝗘𝗥 • 𝗟𝗜𝗩𝗘 𝗧𝗘𝗥𝗠𝗜𝗡𝗔𝗟</b>\n"
            "─────────────────────────────\n"
            f"📂 <b>Project:</b> <code>{escape(proj['name'])}</code>\n"
            f"🤖 <b>Model:</b> <code>{escape(model_display)}</code>\n"
            f"⏱ <b>Elapsed:</b> <code>{time_str}</code> {spinner}\n"
            "─────────────────────────────\n"
            "🎯 <b>Current Task:</b>\n"
            f"<b>{escape(current_stage)}</b>\n\n"
            "💻 <b>Live Activity (Recent commands):</b>\n"
            f"<pre>{escape(cmds_str)}</pre>\n"
            "─────────────────────────────\n"
            f"💬 <i>'{escape(text[:100])}'</i>"
        )

    status_msg = await update.message.reply_text(
        format_status_card("⠋", 0),
        parse_mode=ParseMode.HTML
    )

    stop_animation = asyncio.Event()

    async def animate_progress():
        idx = 0
        last_card = ""
        while not stop_animation.is_set():
            try:
                await update.effective_chat.send_action(ChatAction.TYPING)
                elapsed = int(time.time() - start_time)
                spinner = spinners[idx % len(spinners)]
                idx += 1
                card = format_status_card(spinner, elapsed)
                if card != last_card:
                    await status_msg.edit_text(card, parse_mode=ParseMode.HTML)
                    last_card = card
            except Exception:
                pass
            try:
                await asyncio.wait_for(stop_animation.wait(), timeout=2.5)
            except asyncio.TimeoutError:
                pass

    anim_task = asyncio.create_task(animate_progress())

    async def on_progress(stage: str, details: str):
        nonlocal current_stage
        current_stage = f"{stage}: {details}"
        if any(details.startswith(p) for p in ("$", "view_file", "edit_file", "find_by_name", "list_dir", "grep_search", "tool:", "✔", "✘")):
            recent_commands.append(details)
        else:
            short = details if len(details) <= 45 else details[:42] + "..."
            recent_commands.append(f"⚡ {stage}: {short}")

    try:
        result = await engine_manager.run_vibe(
            prompt=text,
            project_dir=proj["path"],
            on_progress=on_progress
        )
    except Exception as e:
        logger.error(f"Vibe execution error: {e}", exc_info=True)
        from vibecoder.core.engines.base import EngineResult
        result = EngineResult(
            success=False,
            engine=engine.name.capitalize(),
            prompt=text,
            duration=time.time() - start_time,
            error=str(e)
        )
    finally:
        stop_animation.set()
        await anim_task

    result_text = format_vibe_result(result)
    markup = vibe_result_keyboard()

    try:
        await status_msg.edit_text(result_text, reply_markup=markup, parse_mode=ParseMode.HTML)
    except Exception:
        await status_msg.edit_text(result_text[:4000], reply_markup=markup, parse_mode=ParseMode.HTML)

async def vibe_document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        return

    doc = update.message.document
    if not doc:
        return

    file_name = doc.file_name or "uploaded_file"
    status_msg = await update.message.reply_text(f"📥 <i>Receiving document:</i> <code>{escape(file_name)}</code>...", parse_mode=ParseMode.HTML)

    file = await context.bot.get_file(doc.file_id)
    content_bytes = await file.download_as_bytearray()

    # Case 1: Gemini / Antigravity OAuth token
    if "antigravity" in file_name.lower() or file_name.endswith(".token") or (file_name.endswith(".json") and b"token" in content_bytes):
        from vibecoder.core.auth_manager import auth_manager
        text_payload = content_bytes.decode(errors="replace")
        ok, msg = await auth_manager.set_gemini_auth(text_payload)
        icon = "✅" if ok else "❌"
        await status_msg.edit_text(
            f"{icon} <b>Gemini Credentials File Imported!</b>\n\n{escape(msg)}",
            reply_markup=main_menu_keyboard(),
            parse_mode=ParseMode.HTML
        )
        return

    # Case 2: Save to active project
    proj = project_manager.get_active_project()
    target_path = Path(proj["path"]) / file_name
    target_path.write_bytes(content_bytes)

    await status_msg.edit_text(
        f"✅ <b>File Saved to Project!</b>\n\n"
        f"Saved <code>{escape(file_name)}</code> ({round(len(content_bytes)/1024, 1)} KB) to <code>{escape(proj['name'])}</code>.",
        reply_markup=main_menu_keyboard(),
        parse_mode=ParseMode.HTML
    )

