"""
GitHub Copilot CLI Engine implementation (Student Plan / Auto Luna).
Executes prompts autonomously using official Copilot CLI.
"""

import asyncio
import os
import time
from typing import Optional

from vibecoder.config import COPILOT_BIN, settings
from vibecoder.core.engines.base import BaseEngine, EngineResult
from vibecoder.core import git_ops, test_runner
from vibecoder.core.shell_runner import strip_ansi

class CopilotEngine(BaseEngine):
    """GitHub Copilot CLI runner with automated tool approval."""

    @property
    def name(self) -> str:
        return "copilot"

    @property
    def description(self) -> str:
        return f"GitHub Copilot CLI ({settings.get('copilot_model', 'auto')})"

    async def run(self, prompt: str, project_dir: str, **kwargs) -> EngineResult:
        start_time = time.time()
        model = kwargs.get("model") or settings.get("copilot_model", "auto")
        timeout = kwargs.get("timeout") or settings.get("timeout_seconds", 300)
        on_progress = kwargs.get("on_progress")

        if on_progress:
            await on_progress("Copilot", f"GitHub Copilot ({model}) is analyzing project and generating code...")

        st_before = git_ops.get_status(project_dir)

        enhanced_prompt = (
            f"You are operating in directory: {project_dir}\n"
            f"Task: {prompt}\n\n"
            "Instructions:\n"
            "- Directly write or modify the files in this project directory.\n"
            "- If unit tests exist, make sure they remain valid or update them."
        )

        cmd = [
            COPILOT_BIN,
            "-p", enhanced_prompt,
            "--allow-all",
            "--silent"
        ]
        if model and model != "auto":
            cmd.extend(["--model", model])

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

            return EngineResult(
                success=success,
                engine=f"Copilot ({model})",
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
            return EngineResult(
                success=False,
                engine="Copilot",
                prompt=prompt,
                duration=time.time() - start_time,
                error=f"Copilot timed out after {timeout} seconds."
            )
        except Exception as e:
            return EngineResult(
                success=False,
                engine="Copilot",
                prompt=prompt,
                duration=time.time() - start_time,
                error=f"Copilot execution error: {str(e)}"
            )
