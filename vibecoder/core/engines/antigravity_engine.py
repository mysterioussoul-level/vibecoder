"""
Antigravity Engine implementation (Gemini 3.8 Flash High).
Harnesses Google DeepMind Antigravity CLI for autonomous reasoning.
"""

import asyncio
import os
import time
from typing import Optional, List
from pathlib import Path

from vibecoder.config import AGY_BIN, settings
from vibecoder.core.engines.base import BaseEngine, EngineResult
from vibecoder.core import git_ops, test_runner
from vibecoder.core.shell_runner import strip_ansi

class AntigravityEngine(BaseEngine):
    """Antigravity CLI runner powered by Gemini 3.8 (High)."""

    @property
    def name(self) -> str:
        return "antigravity"

    @property
    def description(self) -> str:
        return f"Antigravity CLI ({settings.get('agy_model', 'gemini-3.8-flash-medium')})"

    async def run(self, prompt: str, project_dir: str, **kwargs) -> EngineResult:
        start_time = time.time()
        proj_path = str(Path(project_dir).resolve())
        effort = (kwargs.get("effort") or settings.get("agy_effort", "medium")).lower()
        base_model = kwargs.get("model") or settings.get("agy_model", "gemini-3.8-flash-medium")

        # Harmonize model name with desired effort to avoid CLI conflict
        if any(base_model.endswith(suf) for suf in ("-high", "-medium", "-low")):
            prefix = base_model.rsplit("-", 1)[0]
            model = f"{prefix}-{effort}"
        else:
            model = base_model

        timeout = kwargs.get("timeout") or settings.get("timeout_seconds", 360)
        on_progress = kwargs.get("on_progress")

        if on_progress:
            await on_progress("Planning", f"Gemini 3.8 ({effort} effort) is inspecting files in {Path(project_dir).name}...")

        st_before = git_ops.get_status(project_dir)

        enhanced_prompt = (
            f"You are working in: {proj_path}\n"
            f"User Goal: {prompt}\n\n"
            "Requirements:\n"
            "1. Inspect the existing code in this project directory.\n"
            "2. Directly create or edit the necessary files in this directory to fulfill the request.\n"
            "3. If unit tests exist (e.g. pytest or test files), ensure they pass or update them.\n"
            "4. Provide a concise summary of the changes made."
        )

        cmd = [
            AGY_BIN,
            "-p", enhanced_prompt,
            "--add-dir", proj_path,
            "--mode", "accept-edits",
            "--model", model,
            "--dangerously-skip-permissions"
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=project_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=os.environ.copy()
            )

            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            duration = time.time() - start_time

            out_text = strip_ansi((stdout.decode("utf-8", errors="replace") + "\n" + stderr.decode("utf-8", errors="replace"))).strip()
            success = (proc.returncode == 0)

            st_after = git_ops.get_status(project_dir)
            modified = [f for f in st_after.get("all_changes", []) if f not in st_before.get("all_changes", []) or f in st_after.get("modified", [])]
            if not modified:
                modified = st_after.get("all_changes", [])

            diff_stat = git_ops.get_diff_stat(project_dir)

            test_rep = None
            if settings.get("auto_test", True):
                test_rep = test_runner.run_project_tests(project_dir)

            if not success and modified and test_rep and test_rep.passed:
                success = True

            return EngineResult(
                success=success,
                engine=f"Antigravity ({model})",
                prompt=prompt,
                output=out_text,
                modified_files=modified,
                diff_stat=diff_stat,
                test_report=test_rep,
                duration=duration,
                error="" if success else out_text
            )

        except asyncio.TimeoutError:
            try:
                proc.kill()
            except Exception:
                pass
            st_after = git_ops.get_status(project_dir)
            modified = [f for f in st_after.get("all_changes", []) if f not in st_before.get("all_changes", []) or f in st_after.get("modified", [])]
            if not modified:
                modified = st_after.get("all_changes", [])
            diff_stat = git_ops.get_diff_stat(project_dir)
            test_rep = None
            if settings.get("auto_test", True):
                test_rep = test_runner.run_project_tests(project_dir)
            has_working_code = bool(modified and test_rep and test_rep.passed)
            return EngineResult(
                success=has_working_code,
                engine=f"Antigravity ({model})",
                prompt=prompt,
                output="Antigravity applied code edits before reaching timeout." if has_working_code else "",
                modified_files=modified,
                diff_stat=diff_stat,
                test_report=test_rep,
                duration=time.time() - start_time,
                error="" if has_working_code else f"Antigravity timed out after {timeout} seconds."
            )
        except Exception as e:
            return EngineResult(
                success=False,
                engine="Antigravity",
                prompt=prompt,
                duration=time.time() - start_time,
                error=f"Antigravity execution error: {str(e)}"
            )
