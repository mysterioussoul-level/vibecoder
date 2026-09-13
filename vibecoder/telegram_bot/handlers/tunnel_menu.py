"""
Telegram Bot handlers for Cloudflare Hosting & Port Tunnels.
Allows 1-click public HTTPS exposure for local dev servers and APIs.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from vibecoder.core.tunnel_manager import tunnel_manager
from vibecoder.core.project_manager import project_manager
from vibecoder.telegram_bot.ui.formatters import escape, format_tunnels_view
from vibecoder.telegram_bot.ui.keyboards import tunnels_menu_keyboard
from vibecoder.telegram_bot.handlers.start import is_authorized

logger = logging.getLogger("TunnelHandlers")

async def tunnels_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Render Cloudflare Tunnels & Localhost Hosting dashboard."""
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        return

    proj = project_manager.get_active_project()
    tunnels = tunnel_manager.list_tunnels()
    ports = tunnel_manager.get_active_ports()

    text = format_tunnels_view(tunnels, ports, proj.get("name", "Unknown"))
    markup = tunnels_menu_keyboard(tunnels, ports)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    else:
        await update.message.reply_text(text, reply_markup=markup, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

async def tunnel_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start Cloudflare tunnel for selected port."""
    query = update.callback_query
    await query.answer("🚀 Initializing Cloudflare quick tunnel...")

    port_str = query.data.split(":", 1)[1]
    try:
        port = int(port_str)
    except ValueError:
        return

    status_msg = await query.message.reply_text(
        f"⏳ <b>Connecting port {port} to Cloudflare Edge Network...</b>",
        parse_mode=ParseMode.HTML
    )

    ok, msg, url = await tunnel_manager.start_tunnel(port)
    if ok and url:
        await status_msg.edit_text(
            f"✅ <b>Cloudflare Tunnel Live!</b>\n"
            f"─────────────────────────────\n"
            f"🔌 <b>Port:</b> <code>{port}</code>\n"
            f"🌐 <b>Public URL:</b> <a href=\"{url}\">{escape(url)}</a>\n\n"
            f"<i>Your local service is now reachable anywhere worldwide via secure HTTPS!</i>",
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=False
        )
    else:
        await status_msg.edit_text(
            f"❌ <b>Tunnel Creation Failed:</b>\n<pre>{escape(msg)}</pre>",
            parse_mode=ParseMode.HTML
        )

    # Refresh tunnels dashboard
    proj = project_manager.get_active_project()
    tunnels = tunnel_manager.list_tunnels()
    ports = tunnel_manager.get_active_ports()
    text = format_tunnels_view(tunnels, ports, proj.get("name", "Unknown"))
    markup = tunnels_menu_keyboard(tunnels, ports)
    try:
        await query.edit_message_text(text, reply_markup=markup, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    except Exception:
        pass

async def tunnel_stop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop active tunnel for port."""
    query = update.callback_query
    port_str = query.data.split(":", 1)[1]
    try:
        port = int(port_str)
    except ValueError:
        return

    ok, msg = tunnel_manager.stop_tunnel(port)
    await query.answer(msg)

    proj = project_manager.get_active_project()
    tunnels = tunnel_manager.list_tunnels()
    ports = tunnel_manager.get_active_ports()
    text = format_tunnels_view(tunnels, ports, proj.get("name", "Unknown"))
    markup = tunnels_menu_keyboard(tunnels, ports)
    try:
        await query.edit_message_text(text, reply_markup=markup, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    except Exception:
        pass

async def tunnel_serve_project_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Auto-detect server, run project in background, and create Cloudflare tunnel."""
    query = update.callback_query
    await query.answer("🚀 Launching project server...")

    proj = project_manager.get_active_project()
    proj_path = proj.get("path")

    status_msg = await query.message.reply_text(
        f"⚙️ <b>Auto-detecting and launching server for <code>{escape(proj['name'])}</code>...</b>",
        parse_mode=ParseMode.HTML
    )

    ok, srv_msg, port = await tunnel_manager.auto_serve_project(proj_path)
    if not ok or not port:
        await status_msg.edit_text(f"❌ <b>Server Launch Failed:</b>\n{escape(srv_msg)}", parse_mode=ParseMode.HTML)
        return

    await status_msg.edit_text(
        f"✅ <b>Server Started!</b>\n"
        f"{escape(srv_msg)}\n"
        f"⏳ <i>Connecting Cloudflare tunnel to port {port}...</i>",
        parse_mode=ParseMode.HTML
    )

    t_ok, t_msg, url = await tunnel_manager.start_tunnel(port, proj.get("name"))
    if t_ok and url:
        await status_msg.edit_text(
            f"🎉 <b>App Live on Cloudflare!</b>\n"
            f"─────────────────────────────\n"
            f"📂 <b>Project:</b> <code>{escape(proj['name'])}</code>\n"
            f"🔌 <b>Local Port:</b> <code>{port}</code>\n"
            f"🌐 <b>Public HTTPS:</b> <a href=\"{url}\">{escape(url)}</a>\n\n"
            f"💡 <i>Share this URL to access your app from your phone, browser, or anywhere on the web!</i>",
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=False
        )
    else:
        await status_msg.edit_text(
            f"⚠️ <b>Server running on port {port}</b>, but tunnel failed:\n{escape(t_msg)}",
            parse_mode=ParseMode.HTML
        )

    # Refresh dashboard
    tunnels = tunnel_manager.list_tunnels()
    ports = tunnel_manager.get_active_ports()
    text = format_tunnels_view(tunnels, ports, proj.get("name", "Unknown"))
    markup = tunnels_menu_keyboard(tunnels, ports)
    try:
        await query.edit_message_text(text, reply_markup=markup, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    except Exception:
        pass

async def serve_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Direct command /serve or /run: runs active project and tunnels it immediately."""
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        return

    proj = project_manager.get_active_project()
    proj_path = proj.get("path")

    # Optional port from argument, e.g. /serve 3000
    custom_port = None
    if context.args and len(context.args) > 0:
        try:
            custom_port = int(context.args[0])
        except ValueError:
            pass

    status_msg = await update.message.reply_text(
        f"🚀 <b>Starting & Hosting <code>{escape(proj['name'])}</code>...</b>",
        parse_mode=ParseMode.HTML
    )

    ok, srv_msg, port = await tunnel_manager.auto_serve_project(proj_path, custom_port)
    if not ok or not port:
        await status_msg.edit_text(f"❌ <b>Failed to start server:</b>\n{escape(srv_msg)}", parse_mode=ParseMode.HTML)
        return

    t_ok, t_msg, url = await tunnel_manager.start_tunnel(port, proj.get("name"))
    if t_ok and url:
        await status_msg.edit_text(
            f"🎉 <b>Project Live on Cloudflare!</b>\n"
            f"─────────────────────────────\n"
            f"📂 <b>Project:</b> <code>{escape(proj['name'])}</code>\n"
            f"🔌 <b>Port:</b> <code>{port}</code>\n"
            f"🌐 <b>Public URL:</b> <a href=\"{url}\">{escape(url)}</a>\n\n"
            f"💡 <i>Your application is publicly accessible worldwide via Cloudflare!</i>",
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=False
        )
    else:
        await status_msg.edit_text(
            f"⚠️ <b>Server running on port {port}</b>, but tunnel error:\n{escape(t_msg)}",
            parse_mode=ParseMode.HTML
        )
