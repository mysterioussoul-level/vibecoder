"""
Safe shell command runner for VibeCoder.
Executes terminal commands inside active project directory.
"""

import asyncio
import re
import time
from typing import Tuple

ANSI_ESCAPE_RE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from terminal output."""
    return ANSI_ESCAPE_RE.sub('', text)

async def execute_shell(cmd: str, cwd: str, timeout: int = 120) -> Tuple[int, str, float]:
    """Execute a shell command asynchronously inside cwd."""
    start = time.time()
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            duration = time.time() - start
            out_decoded = (stdout.decode("utf-8", errors="replace") + "\n" + stderr.decode("utf-8", errors="replace")).strip()
            clean_out = strip_ansi(out_decoded)
            return proc.returncode or 0, clean_out, round(duration, 2)
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            duration = time.time() - start
            return -1, f"Command timed out after {timeout} seconds.", round(duration, 2)

    except Exception as e:
        duration = time.time() - start
        return -1, f"Execution failed: {str(e)}", round(duration, 2)
