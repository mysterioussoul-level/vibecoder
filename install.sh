#!/usr/bin/env bash
# ==============================================================================
# VibeCoder 1-Click Installer for GitHub Codespaces & Linux
# ==============================================================================
set -eo pipefail

COLOR_GREEN=" [1;32m"
COLOR_CYAN=" [1;36m"
COLOR_YELLOW=" [1;33m"
COLOR_RESET=" [0m"

echo -e "${COLOR_CYAN}╔══════════════════════════════════════════════════════════════╗${COLOR_RESET}"
echo -e "${COLOR_CYAN}║             🚀 VIBECODER 1-CLICK CODESPACE INSTALLER         ║${COLOR_RESET}"
echo -e "${COLOR_CYAN}╚══════════════════════════════════════════════════════════════╝${COLOR_RESET}"
echo ""

# 1. Install Python packages
echo -e "${COLOR_CYAN}[1/4] Installing Python requirements...${COLOR_RESET}"
python3 -m pip install -q --upgrade pip
python3 -m pip install -q -r requirements.txt

# 2. Make scripts executable
echo -e "${COLOR_CYAN}[2/4] Setting execution permissions...${COLOR_RESET}"
chmod +x run_vibecoder.sh set_vibe_token.sh transport.sh install.sh 2>/dev/null || true

# 3. Verify / Discover AI Engines
echo -e "${COLOR_CYAN}[3/4] Checking AI Engines...${COLOR_RESET}"
if command -v agy >/dev/null 2>&1; then
    echo -e "  ${COLOR_GREEN}✓ Google Antigravity CLI (agy) found${COLOR_RESET}"
else
    echo -e "  ${COLOR_YELLOW}○ agy not found in PATH${COLOR_RESET}"
fi

if command -v copilot >/dev/null 2>&1; then
    echo -e "  ${COLOR_GREEN}✓ GitHub Copilot CLI found${COLOR_RESET}"
else
    echo -e "  ${COLOR_YELLOW}○ copilot CLI not found in PATH${COLOR_RESET}"
fi

if command -v aider >/dev/null 2>&1; then
    echo -e "  ${COLOR_GREEN}✓ Aider CLI found${COLOR_RESET}"
else
    echo -e "  Installing Aider via pip..."
    python3 -m pip install -q aider-chat || true
fi

# 4. Prepare directories
echo -e "${COLOR_CYAN}[4/5] Initializing project directories...${COLOR_RESET}"
mkdir -p projects storage/vibecoder

# 5. Setup persistent auto-start on boot & terminal login
echo -e "${COLOR_CYAN}[5/5] Configuring automatic boot & restart recovery...${COLOR_RESET}"
INSTALL_DIR="$(pwd)"
if ! grep -q "VibeCoder Autostart" ~/.bashrc 2>/dev/null; then
    cat << EOF >> ~/.bashrc

# VibeCoder Autostart on shell login / Codespace boot
if [ -f "$INSTALL_DIR/run_vibecoder.sh" ] && ! pgrep -f "vibecoder.telegram_bot.bot" >/dev/null 2>&1; then
    (bash "$INSTALL_DIR/run_vibecoder.sh" --daemon >/dev/null 2>&1 &)
fi
alias vibe-status="$INSTALL_DIR/run_vibecoder.sh --status"
alias vibe-logs="$INSTALL_DIR/run_vibecoder.sh --logs"
alias vibe-start="$INSTALL_DIR/run_vibecoder.sh --daemon"
alias vibe-stop="$INSTALL_DIR/run_vibecoder.sh --stop"
EOF
fi

echo ""
echo -e "${COLOR_GREEN}============================================================${COLOR_RESET}"
echo -e "${COLOR_GREEN}✅ VibeCoder Installation Complete!${COLOR_RESET}"
echo -e "${COLOR_GREEN}============================================================${COLOR_RESET}"
echo ""
echo "Quick Setup:"
echo -e "  1. Set your bot token: ${COLOR_CYAN}./set_vibe_token.sh <YOUR_BOT_TOKEN> <OWNER_ID>${COLOR_RESET}"
echo -e "  2. Run the bot daemon: ${COLOR_CYAN}./run_vibecoder.sh --daemon${COLOR_RESET}"
echo -e "  3. Open Telegram and send ${COLOR_CYAN}/start${COLOR_RESET}"
echo ""
