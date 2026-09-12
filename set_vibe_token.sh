#!/usr/bin/env bash
# ==============================================================================
# VibeCoder Telegram Bot Token & Credentials Configuration Utility
#
# Configures the dedicated Telegram Bot Token for VibeCoder without
# interfering with any other bots or services.
#
# Usage:
#   ./set_vibe_token.sh                  # Interactive prompt
#   ./set_vibe_token.sh <NEW_BOT_TOKEN>  # Direct set
#   ./set_vibe_token.sh <NEW_BOT_TOKEN> <OWNER_ID>
# ==============================================================================

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$SCRIPT_DIR"
ENV_FILE="$WORKSPACE_ROOT/.env.vibe"
MAIN_ENV="$WORKSPACE_ROOT/.env"

COLOR_GREEN="[1;32m"
COLOR_CYAN="[1;36m"
COLOR_YELLOW="[1;33m"
COLOR_RED="[1;31m"
COLOR_RESET="[0m"

NEW_TOKEN="${1:-}"
NEW_OWNER_ID="${2:-}"

update_key() {
    local key="$1"
    local val="$2"
    local file="$3"
    touch "$file"
    if grep -q "^${key}=" "$file" 2>/dev/null; then
        sed -i "s|^${key}=.*|${key}="${val}"|" "$file"
    else
        echo "${key}="${val}"" >> "$file"
    fi
}

if [ -z "$NEW_TOKEN" ]; then
    echo -e "${COLOR_CYAN}╔══════════════════════════════════════════════════════════════════════════╗${COLOR_RESET}"
    echo -e "${COLOR_CYAN}║             🤖 VIBECODER TELEGRAM BOT SETUP UTILITY                      ║${COLOR_RESET}"
    echo -e "${COLOR_CYAN}╚══════════════════════════════════════════════════════════════════════════╝${COLOR_RESET}"
    echo ""
    echo "Tip: Create a free bot in Telegram by messaging @BotFather:"
    echo "  1. Open Telegram -> search @BotFather"
    echo "  2. Send /newbot -> choose name and username"
    echo "  3. Copy the HTTP API token"
    echo ""
    read -p "Enter your Telegram Bot Token: " NEW_TOKEN
    NEW_TOKEN=$(echo "$NEW_TOKEN" | tr -d '[:space:]')
fi

if [ -z "$NEW_TOKEN" ]; then
    echo -e "${COLOR_RED}Error: Token cannot be empty.${COLOR_RESET}"
    exit 1
fi

echo -e "Testing Bot Token with Telegram API..."
BOT_INFO=$(curl -s "https://api.telegram.org/bot${NEW_TOKEN}/getMe" || true)

if echo "$BOT_INFO" | grep -q '"ok":true'; then
    BOT_NAME=$(echo "$BOT_INFO" | grep -o '"first_name":"[^"]*' | cut -d'"' -f4 || echo "Bot")
    BOT_USER=$(echo "$BOT_INFO" | grep -o '"username":"[^"]*' | cut -d'"' -f4 || echo "")
    echo -e "${COLOR_GREEN}✓ Token verified! Connected to: @${BOT_USER} (${BOT_NAME})${COLOR_RESET}"
else
    echo -e "${COLOR_RED}✗ Verification failed! Telegram responded:${COLOR_RESET}"
    echo "$BOT_INFO"
    echo -e "${COLOR_YELLOW}Saving token anyway, but please verify it with @BotFather.${COLOR_RESET}"
fi

update_key "VIBE_BOT_TOKEN" "$NEW_TOKEN" "$ENV_FILE"
update_key "VIBE_BOT_TOKEN" "$NEW_TOKEN" "$MAIN_ENV"

if [ -n "$NEW_OWNER_ID" ]; then
    update_key "OWNER_ID" "$NEW_OWNER_ID" "$ENV_FILE"
    update_key "OWNER_ID" "$NEW_OWNER_ID" "$MAIN_ENV"
    echo -e "${COLOR_GREEN}✓ Owner ID set to: ${NEW_OWNER_ID}${COLOR_RESET}"
fi

echo -e "${COLOR_GREEN}Saved VIBE_BOT_TOKEN to .env.vibe and .env!${COLOR_RESET}"
echo ""
echo -e "To start VibeCoder now, run: ${COLOR_CYAN}./run_vibecoder.sh${COLOR_RESET}"
