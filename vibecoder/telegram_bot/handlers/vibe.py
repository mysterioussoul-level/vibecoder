"""
Vibe Coding prompt processor for VibeCoder Telegram Bot.
Transforms natural language vibes into autonomous code generation, diffing, and testing.
"""

import asyncio
import time
import logging
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

    start_time = time.time()
    current_stage = "Inspecting workspace files & imports..."
    stage_percent = 15
    spinners = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    bar_len = 10

    def make_progress_bar(pct: int) -> str:
        filled = max(0, min(bar_len, int(round((pct / 100) * bar_len))))
        empty = bar_len - filled
        return f"[{'■' * filled}{'□' * empty}] {pct}%"

    def format_status_card(spinner: str, elapsed: int) -> str:
        mins, secs = divmod(elapsed, 60)
        time_str = f"{mins:02d}:{secs:02d}"
        bar = make_progress_bar(stage_percent)
        return (
            "🧠 <b>Vibe Coding in progress...</b>\n"
            "─────────────────────────────\n"
            f"📂 <b>Project:</b> <code>{escape(proj['name'])}</code>\n"
            f"🤖 <b>Engine:</b> <b>{escape(engine.name.capitalize())}</b>\n"
            f"⏱ <b>Elapsed:</b> <code>{time_str}</code> {spinner}\n\n"
            f"🎯 <b>Current Task:</b>\n"
            f"<i>{escape(current_stage)}</i>\n\n"
            f"<code>{bar}</code>\n"
            "─────────────────────────────\n"
            f"💬 <i>'{escape(text[:120])}'</i>"
        )

    status_msg = await update.message.reply_text(
        format_status_card("⠋", 0),
        parse_mode=ParseMode.HTML
    )

    stop_animation = asyncio.Event()

    async def animate_progress():
        idx = 0
        while not stop_animation.is_set():
            try:
                await update.effective_chat.send_action(ChatAction.TYPING)
                elapsed = int(time.time() - start_time)
                spinner = spinners[idx % len(spinners)]
                idx += 1
                card = format_status_card(spinner, elapsed)
                await status_msg.edit_text(card, parse_mode=ParseMode.HTML)
            except Exception:
                pass
            try:
                await asyncio.wait_for(stop_animation.wait(), timeout=3.5)
            except asyncio.TimeoutError:
                pass

    anim_task = asyncio.create_task(animate_progress())

    async def on_progress(stage: str, details: str):
        nonlocal current_stage, stage_percent
        current_stage = f"{stage}: {details}"
        stage_lower = stage.lower()
        if "gemini" in stage_lower or "plan" in stage_lower:
            stage_percent = 35
        elif "copilot" in stage_lower or "aider" in stage_lower or "code" in stage_lower:
            stage_percent = 65
        elif "test" in stage_lower:
            stage_percent = 85
        elif "heal" in stage_lower:
            stage_percent = 70
        else:
            stage_percent = min(stage_percent + 15, 95)

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

