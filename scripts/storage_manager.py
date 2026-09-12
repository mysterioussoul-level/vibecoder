import os
import shutil
import time
import urllib.request
import urllib.error

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STORAGE_DIR = os.environ.get("STORAGE_DIR", os.path.join(ROOT_DIR, "storage"))
JELLYFIN_DIR = os.path.join(STORAGE_DIR, "jellyfin")
PERMANENT_DIR = os.path.join(STORAGE_DIR, "permanent")
TRANSCODE_CACHE_DIR = "/tmp/jellyfin/cache/transcodes"
DOWNLOADS_DIR = os.path.join(STORAGE_DIR, "downloads")
TMP_DIR = os.path.join(STORAGE_DIR, "tmp")
JELLYFIN_API_KEY = "c8389659b8be440ca4c6ee6f2eb29b35"
JELLYFIN_URL = "http://localhost:8096"

MAX_USAGE_PERCENT = 80.0
TARGET_USAGE_PERCENT = 70.0
TRANSCODE_MAX_AGE_SECONDS = 1800  # 30 minutes


def get_disk_usage(path):
    total, used, free = shutil.disk_usage(path)
    return (used / total) * 100


def clean_transcode_cache(force=False):
    """Prune stale or orphaned Jellyfin transcode segment files."""
    if not os.path.exists(TRANSCODE_CACHE_DIR):
        return
    now = time.time()
    cleaned_bytes = 0
    try:
        for root, _, files in os.walk(TRANSCODE_CACHE_DIR):
            for file in files:
                filepath = os.path.join(root, file)
                try:
                    mtime = os.path.getmtime(filepath)
                    if force or (now - mtime > TRANSCODE_MAX_AGE_SECONDS):
                        fsize = os.path.getsize(filepath)
                        os.remove(filepath)
                        cleaned_bytes += fsize
                except Exception:
                    pass
        if cleaned_bytes > 0:
            print(f"[Storage] Cleaned {cleaned_bytes / (1024 * 1024):.1f} MB from transcode cache.")
    except Exception as e:
        print(f"[Storage] Error pruning transcode cache: {e}")


def clean_empty_dirs(directory):
    """Recursively remove empty subdirectories."""
    if not os.path.exists(directory):
        return
    for root, dirs, files in os.walk(directory, topdown=False):
        if root == directory:
            continue
        try:
            if not os.listdir(root):
                os.rmdir(root)
        except Exception:
            pass


def notify_jellyfin_refresh():
    """Trigger a Jellyfin library rescan via API."""
    try:
        url = f"{JELLYFIN_URL}/Library/Refresh?api_key={JELLYFIN_API_KEY}"
        req = urllib.request.Request(url, data=b"", method="POST")
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status in (200, 204):
                print("[Storage] Triggered Jellyfin library refresh successfully.")
    except Exception as e:
        print(f"[Storage] Jellyfin refresh notification skipped: {e}")


def get_files_sorted_by_age(directory):
    files_with_age = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            filepath = os.path.join(root, file)
            try:
                files_with_age.append((filepath, os.path.getmtime(filepath)))
            except Exception:
                pass
    return sorted(files_with_age, key=lambda x: x[1])


def manage_storage():
    os.makedirs(JELLYFIN_DIR, exist_ok=True)
    os.makedirs(PERMANENT_DIR, exist_ok=True)

    # Clean transcode cache first
    clean_transcode_cache(force=False)

    usage = get_disk_usage(ROOT_DIR if os.path.exists(ROOT_DIR) else "/")
    print(f"[Storage] Current workspace storage usage: {usage:.2f}%")

    if usage > MAX_USAGE_PERCENT:
        print(f"[Storage] Storage usage {usage:.2f}% exceeds {MAX_USAGE_PERCENT}%. Initiating cleanup...")
        # Deep transcode clean
        clean_transcode_cache(force=True)

        # Never evict library or permanent media automatically. Downloads and
        # temporary files are disposable; the media library is not.
        oldest_files = get_files_sorted_by_age(DOWNLOADS_DIR)
        oldest_files.extend(get_files_sorted_by_age(TMP_DIR))
        deleted_any = False
        for filepath, _ in oldest_files:
            try:
                os.remove(filepath)
                deleted_any = True
                print(f"[Storage] Deleted old file: {filepath}")

                usage = get_disk_usage(ROOT_DIR if os.path.exists(ROOT_DIR) else "/")
                if usage <= TARGET_USAGE_PERCENT:
                    print(f"[Storage] Target usage reached: {usage:.2f}%. Stopping cleanup.")
                    break
            except Exception as e:
                print(f"[Storage] Error deleting {filepath}: {e}")

        clean_empty_dirs(DOWNLOADS_DIR)
        clean_empty_dirs(TMP_DIR)
        if deleted_any:
            notify_jellyfin_refresh()


if __name__ == "__main__":
    manage_storage()
