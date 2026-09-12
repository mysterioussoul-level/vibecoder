"""
Authentication & Credential Lifecycle Manager for VibeCoder.
Handles inspecting, renewing, replacing, and OAuth device login for:
- Google Gemini 3.8 / Antigravity
- GitHub Copilot CLI (Student / Luna / Auto)
- OpenRouter (Aider)
"""

import asyncio
import json
import os
import re
import urllib.request
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

from vibecoder.config import (
    WORKSPACE_ROOT,
    COPILOT_BIN,
    AGY_BIN,
    OPENROUTER_API_KEY,
    settings
)

GEMINI_TOKEN_FILE = Path("/home/codespace/.gemini/antigravity-cli/antigravity-oauth-token")
ENV_VIBE = WORKSPACE_ROOT / ".env.vibe"
ENV_MAIN = WORKSPACE_ROOT / ".env"

def update_env_file(key: str, val: str, file_path: Path):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    touch = file_path.touch(exist_ok=True)
    content = file_path.read_text(encoding="utf-8", errors="ignore") if file_path.exists() else ""
    lines = content.splitlines()
    found = False
    new_lines = []
    for line in lines:
        if line.startswith(f"{key}="):
            new_lines.append(f'{key}="{val}"')
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f'{key}="{val}"')
    file_path.write_text("\n".join(new_lines).strip() + "\n", encoding="utf-8")

class AuthManager:
    """Manages AI engine credentials and interactive authentication."""

    def __init__(self):
        self.active_login_process: Optional[asyncio.subprocess.Process] = None

    async def check_copilot_auth(self) -> Dict[str, Any]:
        """Check if Copilot CLI has active authorization."""
        try:
            proc = await asyncio.create_subprocess_exec(
                COPILOT_BIN, "-p", "reply pong", "--silent",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=os.environ.copy()
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
            out = (stdout.decode(errors="replace") + " " + stderr.decode(errors="replace")).strip()
            
            if proc.returncode == 0:
                return {
                    "authenticated": True,
                    "status": "Active 🟢",
                    "details": "Authenticated (Student / Auto mode active)"
                }
            else:
                return {
                    "authenticated": False,
                    "status": "Expired / Logged Out 🔴",
                    "details": out[:200] or "Not authenticated"
                }
        except asyncio.TimeoutError:
            return {"authenticated": False, "status": "Timeout 🟡", "details": "Check timed out"}
        except Exception as e:
            return {"authenticated": False, "status": "Error 🔴", "details": str(e)}

    async def check_gemini_auth(self) -> Dict[str, Any]:
        """Check if Antigravity / Gemini 3.8 High is authorized."""
        try:
            proc = await asyncio.create_subprocess_exec(
                AGY_BIN, "-p", "reply pong",
                "--model", "gemini-3.8-flash-high",
                "--dangerously-skip-permissions",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=os.environ.copy()
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=20)
            out = (stdout.decode(errors="replace") + " " + stderr.decode(errors="replace")).strip()

            if proc.returncode == 0:
                return {
                    "authenticated": True,
                    "status": "Active 🟢",
                    "details": "Gemini 3.8 Flash (High) verified and responsive"
                }
            else:
                return {
                    "authenticated": False,
                    "status": "Expired / Credit Exhausted 🔴",
                    "details": out[:200] or "Authentication required"
                }
        except asyncio.TimeoutError:
            return {"authenticated": False, "status": "Timeout 🟡", "details": "Gemini check timed out"}
        except Exception as e:
            return {"authenticated": False, "status": "Error 🔴", "details": str(e)}

    async def check_openrouter_auth(self) -> Dict[str, Any]:
        """Validate OpenRouter API key status and credits."""
        key = os.environ.get("OPENROUTER_API_KEY") or OPENROUTER_API_KEY
        if not key:
            return {
                "authenticated": False,
                "status": "Unset ⚪",
                "details": "OPENROUTER_API_KEY is not configured"
            }

        def _do_req():
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/auth/key",
                headers={"Authorization": f"Bearer {key}"}
            )
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode())
                        return True, data.get("data", {})
                    return False, {}
            except Exception as e:
                return False, {"error": str(e)}

        ok, data = await asyncio.to_thread(_do_req)
        if ok:
            label = data.get("label", "Key Active")
            free = data.get("is_free_tier", False)
            tier_str = "Free Tier" if free else "Paid Tier"
            return {
                "authenticated": True,
                "status": "Active 🟢",
                "details": f"{label} ({tier_str})"
            }
        else:
            return {
                "authenticated": False,
                "status": "Invalid / Expired 🔴",
                "details": data.get("error", "Failed to validate key")
            }

    async def check_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Check all 3 engines concurrently."""
        gemini_task = self.check_gemini_auth()
        copilot_task = self.check_copilot_auth()
        openrouter_task = self.check_openrouter_auth()

        g_res, c_res, o_res = await asyncio.gather(gemini_task, copilot_task, openrouter_task)
        return {
            "gemini": g_res,
            "copilot": c_res,
            "openrouter": o_res,
        }

    async def start_copilot_device_login(self) -> Tuple[bool, str, str, Optional[asyncio.subprocess.Process]]:
        """
        Initiate Copilot CLI OAuth Device Code login.
        Returns (success, verification_url, user_code, process).
        """
        if self.active_login_process and self.active_login_process.returncode is None:
            try:
                self.active_login_process.kill()
            except Exception:
                pass

        try:
            proc = await asyncio.create_subprocess_exec(
                COPILOT_BIN, "login", "--device-code",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=os.environ.copy()
            )
            self.active_login_process = proc

            url = "https://github.com/login/device"
            code = ""

            for _ in range(30):
                line = await asyncio.wait_for(proc.stdout.readline(), timeout=5)
                if not line:
                    break
                text = line.decode(errors="replace").strip()
                m_code = re.search(r"code\s+([A-Z0-9]{4}-[A-Z0-9]{4})", text, re.IGNORECASE)
                m_url = re.search(r"(https://github\.com/login/device)", text)
                if m_code:
                    code = m_code.group(1)
                if m_url:
                    url = m_url.group(1)
                if code:
                    return True, url, code, proc

            return False, "", "Could not extract login device code from Copilot CLI.", None

        except Exception as e:
            return False, "", f"Failed to launch Copilot login: {str(e)}", None

    async def set_copilot_token(self, token: str) -> Tuple[bool, str]:
        """Apply a GitHub Personal Access Token or Copilot OAuth token."""
        token = token.strip()
        if not token:
            return False, "Token cannot be empty."

        # Pass token via stdin to copilot login --with-token
        try:
            proc = await asyncio.create_subprocess_exec(
                COPILOT_BIN, "login", "--with-token",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(input=(token + "\n").encode()), timeout=20)
            out = (stdout.decode(errors="replace") + " " + stderr.decode(errors="replace")).strip()

            if proc.returncode == 0:
                # Save to environment files for persistence
                update_env_file("COPILOT_GITHUB_TOKEN", token, ENV_VIBE)
                update_env_file("COPILOT_GITHUB_TOKEN", token, ENV_MAIN)
                os.environ["COPILOT_GITHUB_TOKEN"] = token
                return True, "Successfully authenticated GitHub Copilot CLI!"
            else:
                return False, f"Copilot authentication failed: {out}"

        except Exception as e:
            return False, f"Error setting Copilot token: {str(e)}"

    async def set_gemini_auth(self, token_or_json: str) -> Tuple[bool, str]:
        """
        Update Google Gemini / Antigravity credentials.
        Accepts:
        1. JSON content of antigravity-oauth-token
        2. Raw OAuth access token string
        3. Gemini API Key (AIza...)
        """
        token_or_json = token_or_json.strip()
        if not token_or_json:
            return False, "Credential payload cannot be empty."

        # Case 1: Gemini API Key
        if token_or_json.startswith("AIza"):
            update_env_file("GEMINI_API_KEY", token_or_json, ENV_VIBE)
            update_env_file("GEMINI_API_KEY", token_or_json, ENV_MAIN)
            update_env_file("GOOGLE_API_KEY", token_or_json, ENV_VIBE)
            update_env_file("GOOGLE_API_KEY", token_or_json, ENV_MAIN)
            os.environ["GEMINI_API_KEY"] = token_or_json
            os.environ["GOOGLE_API_KEY"] = token_or_json
            return True, "Updated GEMINI_API_KEY and GOOGLE_API_KEY in environment!"

        # Case 2: JSON payload
        GEMINI_TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            parsed = json.loads(token_or_json)
            GEMINI_TOKEN_FILE.write_text(json.dumps(parsed, indent=2), encoding="utf-8")
        except json.JSONDecodeError:
            # Case 3: Raw token string -> construct standard structure
            token_obj = {
                "token": token_or_json,
                "auth_method": "oauth",
                "id_token": ""
            }
            GEMINI_TOKEN_FILE.write_text(json.dumps(token_obj, indent=2), encoding="utf-8")

        # Verify new auth
        chk = await self.check_gemini_auth()
        if chk["authenticated"]:
            return True, "Successfully updated and verified Gemini 3.8 / Antigravity credentials!"
        return True, f"Saved credentials to {GEMINI_TOKEN_FILE}. (Verification note: {chk['details']})"

    async def set_openrouter_key(self, api_key: str) -> Tuple[bool, str]:
        """Validate and apply a new OpenRouter API Key."""
        api_key = api_key.strip()
        if not api_key:
            return False, "API key cannot be empty."

        # Test key validity
        def _test():
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/auth/key",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    return resp.status == 200
            except Exception:
                return False

        valid = await asyncio.to_thread(_test)
        if not valid:
            return False, "Invalid OpenRouter API Key. Verification returned error."

        update_env_file("OPENROUTER_API_KEY", api_key, ENV_VIBE)
        update_env_file("OPENROUTER_API_KEY", api_key, ENV_MAIN)
        os.environ["OPENROUTER_API_KEY"] = api_key
        return True, "OpenRouter API Key verified and saved successfully!"

auth_manager = AuthManager()
