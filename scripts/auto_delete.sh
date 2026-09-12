#!/bin/bash
# Deletes files older than 15 days in the tmp folder, but leaves the permanent folder alone.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MEDIA_DIR="${STORAGE_DIR:-$WORKSPACE_ROOT/storage}"
TMP_DIR="${MEDIA_DIR}/tmp"
PERM_DIR="${MEDIA_DIR}/permanent"

mkdir -p "$TMP_DIR" "$PERM_DIR"

echo "Running 15-day cleanup on $TMP_DIR..."
# Find files older than 15 days and delete them
find "$TMP_DIR" -type f -mtime +15 -exec rm -f {} \;

echo "Cleanup complete."
