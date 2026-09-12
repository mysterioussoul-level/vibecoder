#!/bin/bash
# ==============================================================================
# Background watchdog script for automatic storage, container health, and visibility
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BOT_DIR="$WORKSPACE_ROOT/mirror-leech-telegram-bot"
STORAGE_DIR="$WORKSPACE_ROOT/storage"
COMPOSE_FILE="$BOT_DIR/docker-compose.yml"
STORAGE_SCRIPT="$SCRIPT_DIR/storage_manager.py"
AUTO_DELETE_SCRIPT="$SCRIPT_DIR/auto_delete.sh"
LOG_FILE="/tmp/watchdog.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting Playground Watchdog Daemon..." >> "$LOG_FILE"

while true; do
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

    # 0. Ensure Jellyfin cache permissions survive reboots
    sudo mkdir -p /tmp/jellyfin/cache /tmp/jellyfin/transcodes >/dev/null 2>&1 || true
    sudo chmod -R 777 /tmp/jellyfin >/dev/null 2>&1 || true

    # 1. Run storage manager
    if [ -f "$STORAGE_SCRIPT" ]; then
        python3 "$STORAGE_SCRIPT" >> /tmp/storage_manager.log 2>&1
    fi

    # 2. Run auto delete on temp dir
    if [ -f "$AUTO_DELETE_SCRIPT" ]; then
        bash "$AUTO_DELETE_SCRIPT" >> /tmp/auto_delete.log 2>&1
    fi

    # 3. Check container health
    for CONTAINER in mirror-leech-bot jellyfin bgutil-provider; do
        STATUS=$(docker inspect --format='{{.State.Status}}' "$CONTAINER" 2>/dev/null || echo "missing")
        if [ "$STATUS" != "running" ]; then
            echo "[$TIMESTAMP] Watchdog: Container $CONTAINER is $STATUS, restarting via docker compose..." >> "$LOG_FILE"
            docker compose -f "$COMPOSE_FILE" up -d >> "$LOG_FILE" 2>&1
            break
        fi
    done

    # 4. Maintain Cloudflare Tunnel for Jellyfin (instant, public streaming)
    if command -v cloudflared >/dev/null 2>&1; then
        if ! pgrep -f "cloudflared tunnel" >/dev/null 2>&1; then
            echo "[$TIMESTAMP] Watchdog: Launching cloudflared tunnel for port 8096..." >> "$LOG_FILE"
            nohup cloudflared tunnel --url http://localhost:8096 > /tmp/cloudflared.log 2>&1 &
            sleep 4
        fi
        CF_URL=$(grep -o "https://[a-zA-Z0-9-]*\.trycloudflare\.com" /tmp/cloudflared.log 2>/dev/null | tail -n 1)
        if [ -n "$CF_URL" ]; then
            for UP_PATH in /storage/jellyfin_url.txt "$STORAGE_DIR/jellyfin_url.txt" "$BOT_DIR/jellyfin_url.txt" /tmp/jellyfin_url.txt; do
                CURR_VAL=$(cat "$UP_PATH" 2>/dev/null || true)
                if [ "$CURR_VAL" != "$CF_URL" ]; then
                    echo "$CF_URL" > "$UP_PATH" 2>/dev/null || true
                fi
            done
        fi
    fi

    # 5. Keep port 8096 public in Codespaces
    if [ -n "$CODESPACE_NAME" ]; then
        gh codespace ports visibility 8096:public -c "$CODESPACE_NAME" > /dev/null 2>&1 || true
    fi

    # 6. Maintain VibeCoder Autonomous Studio Daemon
    if [ -f "$WORKSPACE_ROOT/run_vibecoder.sh" ]; then
        if ! pgrep -f "vibecoder.telegram_bot.bot" >/dev/null 2>&1; then
            echo "[$TIMESTAMP] Watchdog: VibeCoder process not detected, starting daemon..." >> "$LOG_FILE"
            bash "$WORKSPACE_ROOT/run_vibecoder.sh" --daemon >> "$LOG_FILE" 2>&1 || true
        fi
    fi

    echo "[$TIMESTAMP] Heartbeat OK - services verified" >> "$LOG_FILE"
    sleep 120
done
