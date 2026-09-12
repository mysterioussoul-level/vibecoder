"""
Configuration and settings manager for Autonomous Vibe Coding System.
Handles environment variables, persistent state, engine preferences, and paths.
"""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import dotenv_values

WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", "/workspaces/playground")).resolve()
PROJECTS_DIR = Path(os.environ.get("VIBECODER_PROJECTS_DIR", WORKSPACE_ROOT / "projects")).resolve()
STORAGE_DIR = Path(WORKSPACE_ROOT / "storage" / "vibecoder").resolve()
SETTINGS_FILE = STORAGE_DIR / "settings.json"
STATE_FILE = STORAGE_DIR / "state.json"

STORAGE_DIR.mkdir(parents=True, exist_ok=True)
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

CODESPACE_NAME = (
    os.environ.get("CODESPACE_NAME")
    or os.environ.get("HOSTNAME")
    or "codespace-local"
)

# Load environment configuration with strict process isolation.
# VibeCoder uses .env.vibe to prevent colliding with other bots (e.g. Docker mirror-leech-bot).
_vibe_env_file = WORKSPACE_ROOT / ".env.vibe"
_general_env_file = WORKSPACE_ROOT / ".env"

_vibe_dict = dotenv_values(_vibe_env_file) if _vibe_env_file.exists() else {}
_general_dict = dotenv_values(_general_env_file) if _general_env_file.exists() else {}

def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """Retrieve environment variable checking os.environ, then .env.vibe, then general .env."""
    val = os.environ.get(key)
    if val:
        return val.strip()
    if key in _vibe_dict and _vibe_dict[key]:
        return str(_vibe_dict[key]).strip()
    if key in _general_dict and _general_dict[key]:
        return str(_general_dict[key]).strip()
    return default

# Dedicated Telegram Bot Token for VibeCoder
# NEVER falls back to general BOT_TOKEN from .env or external bot token files
# to prevent conflicting with Docker mirror-leech-bot on Telegram polling.
_vibe_token = (
    os.environ.get("VIBE_BOT_TOKEN")
    or _vibe_dict.get("VIBE_BOT_TOKEN")
    or _vibe_dict.get("BOT_TOKEN")  # explicitly placed in .env.vibe
    or os.environ.get("TELEGRAM_BOT_TOKEN")
    or _general_dict.get("VIBE_BOT_TOKEN")
)
TELEGRAM_BOT_TOKEN = str(_vibe_token).strip() if _vibe_token else ""

_owner_raw = get_env("OWNER_ID", "0")
try:
    OWNER_ID = int(_owner_raw)
except (ValueError, TypeError):
    OWNER_ID = 0

OPENROUTER_API_KEY = get_env("OPENROUTER_API_KEY", "")

# Binary discovery
COPILOT_BIN = shutil.which("copilot") or "/usr/bin/copilot"
AGY_BIN = shutil.which("agy") or "/home/codespace/.local/bin/agy"
AIDER_BIN = shutil.which("aider") or shutil.which("aider-chat") or "/home/codespace/.python/current/bin/aider"
GIT_BIN = shutil.which("git") or "/usr/bin/git"
GH_BIN = shutil.which("gh") or "/usr/bin/gh"

DEFAULT_SETTINGS: Dict[str, Any] = {
    "default_engine": "antigravity",
    "agy_model": "gemini-3.8-flash-high",
    "agy_effort": "high",
    "aider_model": "openrouter/deepseek/deepseek-chat",
    "copilot_model": "auto",
    "auto_test": True,
    "auto_git": True,
    "max_iterations": 2,
    "timeout_seconds": 300,
}

class SettingsManager:
    """Manages persistent runtime settings and active project state."""

    def __init__(self):
        self._settings = self._load_settings()
        self._state = self._load_state()

    def _load_settings(self) -> Dict[str, Any]:
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    merged = DEFAULT_SETTINGS.copy()
                    merged.update(data)
                    return merged
            except Exception:
                pass
        return DEFAULT_SETTINGS.copy()

    def _load_state(self) -> Dict[str, Any]:
        default_state = {"active_project": ""}
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return default_state

    def save_settings(self):
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(self._settings, f, indent=2)

    def save_state(self):
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self._state, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        return self._settings.get(key, default)

    def set(self, key: str, value: Any):
        self._settings[key] = value
        self.save_settings()

    @property
    def active_project(self) -> str:
        proj = self._state.get("active_project", "")
        if not proj or not Path(proj).exists():
            # Fallback to first project or workspace root
            subdirs = [d for d in PROJECTS_DIR.iterdir() if d.is_dir() and not d.name.startswith(".")]
            if subdirs:
                proj = str(subdirs[0])
            else:
                proj = str(WORKSPACE_ROOT)
            self.set_active_project(proj)
        return proj

    def set_active_project(self, project_path: str):
        p = Path(project_path).resolve()
        self._state["active_project"] = str(p)
        self.save_state()

settings = SettingsManager()
