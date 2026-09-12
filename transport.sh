#!/usr/bin/env bash
# ==============================================================================
# VibeCoder Codespace Transport & Migration Utility
#
# Seamlessly exports and restores all projects, configs, and AI settings
# across GitHub Codespaces or any remote dev container when credits run out.
#
# Usage:
#   ./transport.sh backup             # Create local .tar.gz backup
#   ./transport.sh restore <FILE>     # Restore workspace from backup file
#   ./transport.sh sync               # Commit & push backup branch to GitHub
# ==============================================================================

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="/workspaces/playground"
if [ ! -d "$WORKSPACE_ROOT" ]; then
    WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi

BACKUP_DIR="$WORKSPACE_ROOT/storage/vibecoder/backups"
mkdir -p "$BACKUP_DIR"

TIMESTAMP="$(date +'%Y%m%d_%H%M%S')"
BACKUP_FILENAME="vibecoder_backup_${TIMESTAMP}.tar.gz"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_FILENAME"
LATEST_LINK="$WORKSPACE_ROOT/vibecoder_backup_latest.tar.gz"

COLOR_GREEN="\033[1;32m"
COLOR_CYAN="\033[1;36m"
COLOR_YELLOW="\033[1;33m"
COLOR_RED="\033[1;31m"
COLOR_RESET="\033[0m"

log_info() { echo -e "${COLOR_CYAN}[INFO]${COLOR_RESET} $1" >&2; }
log_success() { echo -e "${COLOR_GREEN}[SUCCESS]${COLOR_RESET} $1" >&2; }
log_warn() { echo -e "${COLOR_YELLOW}[WARN]${COLOR_RESET} $1" >&2; }
log_error() { echo -e "${COLOR_RED}[ERROR]${COLOR_RESET} $1" >&2; }

create_backup() {
    log_info "Creating complete VibeCoder workspace backup..."

    local items=()
    [ -d "$WORKSPACE_ROOT/projects" ] && items+=("projects")
    [ -d "$WORKSPACE_ROOT/vibecoder" ] && items+=("vibecoder")
    [ -d "$WORKSPACE_ROOT/storage/vibecoder" ] && items+=("storage/vibecoder")
    [ -f "$WORKSPACE_ROOT/.env" ] && items+=(".env")
    [ -f "$WORKSPACE_ROOT/.env.vibe" ] && items+=(".env.vibe")
    [ -f "$WORKSPACE_ROOT/transport.sh" ] && items+=("transport.sh")
    [ -f "$WORKSPACE_ROOT/run_vibecoder.sh" ] && items+=("run_vibecoder.sh")
    [ -f "$WORKSPACE_ROOT/set_vibe_token.sh" ] && items+=("set_vibe_token.sh")

    if [ ${#items[@]} -eq 0 ]; then
        log_error "No VibeCoder items found to back up in $WORKSPACE_ROOT."
        exit 1
    fi

    local tmp_tar="/tmp/$BACKUP_FILENAME"
    tar -czf "$tmp_tar" \
        --exclude='*/__pycache__*' \
        --exclude='*/.pytest_cache*' \
        --exclude='*/node_modules*' \
        --exclude='*/.venv*' \
        --exclude='*/venv*' \
        --exclude='*.pyc' \
        --exclude='*/backups*' \
        --exclude='backups' \
        -C "$WORKSPACE_ROOT" "${items[@]}"
    mv "$tmp_tar" "$BACKUP_PATH"

    ln -sfn "$BACKUP_PATH" "$LATEST_LINK"

    local size
    size=$(du -h "$BACKUP_PATH" | cut -f1)
    log_success "Backup created: $BACKUP_PATH ($size)"
    log_success "Symlinked to: $LATEST_LINK"
    echo "$BACKUP_PATH"
}

restore_backup() {
    local source="${1:-$LATEST_LINK}"
    if [ -z "$source" ]; then
        log_error "Please specify a backup file path."
        echo "Usage: ./transport.sh restore <path_to_tar_gz>"
        exit 1
    fi

    if [ ! -f "$source" ]; then
        log_error "Backup file not found: $source"
        exit 1
    fi

    log_info "Extracting backup into $WORKSPACE_ROOT..."
    mkdir -p "$WORKSPACE_ROOT"
    tar -xzf "$source" -C "$WORKSPACE_ROOT"
    log_success "Extracted backup successfully!"

    restore_environment
}

restore_environment() {
    log_info "Configuring environment dependencies..."
    python3 -m pip install --quiet python-telegram-bot python-dotenv rich fastapi uvicorn pytest httpx || true

    chmod +x "$WORKSPACE_ROOT/transport.sh" 2>/dev/null || true
    chmod +x "$WORKSPACE_ROOT/run_vibecoder.sh" 2>/dev/null || true
    chmod +x "$WORKSPACE_ROOT/set_vibe_token.sh" 2>/dev/null || true
    chmod +x "$WORKSPACE_ROOT/vibecoder/transport/transport.sh" 2>/dev/null || true

    log_success "Environment restored!"
    echo ""
    echo -e "To start VibeCoder: ${COLOR_GREEN}./run_vibecoder.sh${COLOR_RESET}"
}

sync_github() {
    log_info "Syncing VibeCoder and projects to GitHub remote..."
    cd "$WORKSPACE_ROOT"

    if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        log_error "Workspace is not a git repository."
        exit 1
    fi

    local branch="vibecoder-backup"
    git checkout -B "$branch" 2>/dev/null || true
    git add projects/ vibecoder/ transport.sh run_vibecoder.sh set_vibe_token.sh 2>/dev/null || true
    git commit -m "Auto-backup VibeCoder workspace [${TIMESTAMP}]" || true

    log_info "Pushing to remote origin/$branch..."
    if git push origin "$branch" --force 2>/dev/null; then
        log_success "Successfully synced to branch '$branch' on GitHub!"
    else
        log_warn "git push origin failed. Trying default origin HEAD..."
        git push origin HEAD 2>/dev/null || log_warn "Remote push not available without push permissions."
    fi
}

case "${1:-}" in
    backup)
        create_backup
        ;;
    restore)
        restore_backup "${2:-}"
        ;;
    restore-env)
        restore_environment
        ;;
    sync)
        sync_github
        ;;
    *)
        echo -e "${COLOR_CYAN}VibeCoder Migration & Transport Manager${COLOR_RESET}"
        echo "Commands:"
        echo "  ./transport.sh backup             - Create local tarball backup"
        echo "  ./transport.sh restore <FILE>     - Restore workspace from file"
        echo "  ./transport.sh sync               - Commit and push backup branch to GitHub"
        echo "  ./transport.sh restore-env        - Reinstall dependencies in new Codespace"
        ;;
esac
