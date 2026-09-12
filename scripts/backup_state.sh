#!/usr/bin/env bash
set -euo pipefail

# Create a local, restorable backup without transient media/cache data.
# Set BACKUP_DIR to place backups outside the repository.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-${ROOT_DIR}/storage/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
ARCHIVE="${BACKUP_DIR}/playground-state-${STAMP}.tar.gz"

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

tar -czf "$ARCHIVE" \
    --exclude='jellyfin/config/log' \
    --exclude='jellyfin/config/data/*.db-wal' \
    --exclude='jellyfin/config/data/*.db-shm' \
    --exclude='storage/downloads' \
    --exclude='storage/tmp' \
    --exclude='storage/backups' \
    --exclude='mirror-leech-telegram-bot/downloads' \
    --exclude='mirror-leech-telegram-bot/.pytest_cache' \
    --exclude='mirror-leech-telegram-bot/__pycache__' \
    -C "$ROOT_DIR" \
    mirror-leech-telegram-bot/config.py \
    mirror-leech-telegram-bot/rclone.conf \
    mirror-leech-telegram-bot/credentials.json \
    mirror-leech-telegram-bot/token.pickle \
    mirror-leech-telegram-bot/cookies.txt \
    mirror-leech-telegram-bot/qBittorrent/config \
    mirror-leech-telegram-bot/sabnzbd \
    jellyfin/config \
    storage/permanent

chmod 600 "$ARCHIVE"
if ! tar -tzf "$ARCHIVE" >/dev/null; then
    rm -f "$ARCHIVE"
    printf 'Backup verification failed; incomplete archive removed.\n' >&2
    exit 1
fi
find "$BACKUP_DIR" -maxdepth 1 -type f -name 'playground-state-*.tar.gz' \
    -mtime +"$RETENTION_DAYS" -delete

printf 'Created backup: %s\n' "$ARCHIVE"
