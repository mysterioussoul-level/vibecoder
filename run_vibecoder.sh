#!/usr/bin/env bash
# ==============================================================================
# VibeCoder Service & Bot Runner
#
# Launches the autonomous vibe coding control center with background daemon
# capability, automatic dependency verification, and log streaming.
#
# Usage:
#   ./run_vibecoder.sh            # Run in foreground
#   ./run_vibecoder.sh --daemon   # Run in background as daemon
#   ./run_vibecoder.sh --stop     # Stop background daemon
#   ./run_vibecoder.sh --status   # Check status & PID
#   ./run_vibecoder.sh --logs     # Stream daemon logs
#   ./run_vibecoder.sh --cli      # Run interactive terminal CLI (no Telegram needed)
# ==============================================================================

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$SCRIPT_DIR"
PID_FILE="$WORKSPACE_ROOT/storage/vibecoder/vibecoder.pid"
LOG_FILE="$WORKSPACE_ROOT/storage/vibecoder/vibecoder.log"

COLOR_GREEN="[1;32m"
COLOR_CYAN="[1;36m"
COLOR_YELLOW="[1;33m"
COLOR_RED="[1;31m"
COLOR_RESET="[0m"

mkdir -p "$WORKSPACE_ROOT/storage/vibecoder"

export PYTHONPATH="$WORKSPACE_ROOT:$PYTHONPATH"

check_token() {
    # Check if token is available
    if [ -f "$WORKSPACE_ROOT/.env.vibe" ]; then
        export $(grep -v '^#' "$WORKSPACE_ROOT/.env.vibe" | xargs -d '
' 2>/dev/null || true)
    fi
    if [ -f "$WORKSPACE_ROOT/.env" ]; then
        export $(grep -v '^#' "$WORKSPACE_ROOT/.env" | xargs -d '
' 2>/dev/null || true)
    fi

    local tok="${VIBE_BOT_TOKEN:-${TELEGRAM_BOT_TOKEN:-}}"
    if [ -z "$tok" ]; then
        echo -e "${COLOR_YELLOW}[WARNING] No Telegram Bot Token configured!${COLOR_RESET}"
        echo -e "To use Telegram interface, run: ${COLOR_CYAN}./set_vibe_token.sh <YOUR_TOKEN>${COLOR_RESET}"
        echo -e "Starting in interactive CLI mode instead...
"
        exec python3 -m vibecoder.cli
    fi
}

start_foreground() {
    check_token
    echo -e "${COLOR_GREEN}Starting VibeCoder Telegram Control Center in foreground...${COLOR_RESET}"
    exec python3 -m vibecoder.telegram_bot.bot
}

start_daemon() {
    check_token
    if pgrep -f "vibecoder.telegram_bot.bot" >/dev/null 2>&1; then
        local pid
        pid=$(pgrep -f "vibecoder.telegram_bot.bot" | head -n 1)
        echo -e "${COLOR_YELLOW}VibeCoder is already running (PID: $pid).${COLOR_RESET}"
        return 0
    fi

    echo -e "${COLOR_CYAN}Starting VibeCoder crash-resilient supervisor daemon...${COLOR_RESET}"
    setsid -f bash -c '
    cd "'"$WORKSPACE_ROOT"'"
    export PYTHONPATH="'"$WORKSPACE_ROOT"':$PYTHONPATH"
    while true; do
        echo "[$(date "+%Y-%m-%d %H:%M:%S")] [Supervisor] Launching VibeCoder Bot..." >> "'"$LOG_FILE"'"
        python3 -u -m vibecoder.telegram_bot.bot >> "'"$LOG_FILE"'" 2>&1
        EXIT_CODE=$?
        echo "[$(date "+%Y-%m-%d %H:%M:%S")] [Supervisor] VibeCoder process exited (code $EXIT_CODE). Restarting in 3s..." >> "'"$LOG_FILE"'"
        sleep 3
    done
    ' >/dev/null 2>&1

    sleep 3

    if pgrep -f "vibecoder.telegram_bot.bot" >/dev/null 2>&1; then
        local b_pid
        b_pid=$(pgrep -f "vibecoder.telegram_bot.bot" | head -n 1)
        echo "$b_pid" > "$PID_FILE"
        echo -e "${COLOR_GREEN}✓ VibeCoder supervisor active! (PID: $b_pid)${COLOR_RESET}"
        echo -e "Logs: ${COLOR_YELLOW}$LOG_FILE${COLOR_RESET}"
    else
        echo -e "${COLOR_RED}✗ Failed to start. Check logs:${COLOR_RESET}"
        tail -n 20 "$LOG_FILE"
    fi
}

stop_daemon() {
    if [ -f "$PID_FILE" ]; then
        local pid
        pid=$(cat "$PID_FILE" 2>/dev/null || true)
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            echo -e "Stopping VibeCoder supervisor (PID: $pid)..."
            kill "$pid" 2>/dev/null || true
        fi
        rm -f "$PID_FILE"
    fi
    pkill -f "vibecoder.telegram_bot.bot" 2>/dev/null || true
    pkill -f "Supervisor.*vibecoder" 2>/dev/null || true
    echo -e "${COLOR_GREEN}✓ VibeCoder stopped.${COLOR_RESET}"
}

check_status() {
    if pgrep -f "vibecoder.telegram_bot.bot" >/dev/null 2>&1; then
        local pid
        pid=$(pgrep -f "vibecoder.telegram_bot.bot" | head -n 1)
        echo -e "${COLOR_GREEN}● VibeCoder is RUNNING${COLOR_RESET} (PID: $pid)"
        return 0
    elif [ -f "$PID_FILE" ]; then
        local pid
        pid=$(cat "$PID_FILE" 2>/dev/null || true)
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            echo -e "${COLOR_GREEN}● VibeCoder supervisor is RUNNING${COLOR_RESET} (PID: $pid)"
            return 0
        fi
    fi
    echo -e "${COLOR_RED}○ VibeCoder is STOPPED${COLOR_RESET}"
    return 1
}

show_logs() {
    if [ -f "$LOG_FILE" ]; then
        tail -f "$LOG_FILE"
    else
        echo -e "${COLOR_YELLOW}No log file found at $LOG_FILE${COLOR_RESET}"
    fi
}

case "${1:-}" in
    --daemon|-d)
        start_daemon
        ;;
    --stop)
        stop_daemon
        ;;
    --status)
        check_status
        ;;
    --logs|-l)
        show_logs
        ;;
    --cli|-c)
        exec python3 -m vibecoder.cli
        ;;
    *)
        start_foreground
        ;;
esac
