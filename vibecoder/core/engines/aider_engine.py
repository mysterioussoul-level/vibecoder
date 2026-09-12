"""
Aider Engine implementation with OpenRouter integration.
Specialized in precision code editing and git diff generation.
"""

import asyncio
import os
import time
from typing import Optional

from vibecoder.config import AIDER_BIN, OPENROUTER_API_KEY, settings
from vibecoder.core.engines.base import BaseEngine, EngineResult
from vibecoder.core import git_ops, test_runner
from vibecoder.core.shell_runner import strip_ansi

class AiderEngine(BaseEngine):
    """Aider coding agent powered by OpenRouter."""

    @property
    def name(self) -> str:
        return "aider"

    @property
    def description(self) -> str:
        return f"Aider ({settings.get('aider_model', 'openrouter/deepseek/deepseek-chat')})"

    async def run(self, prompt: str, project_dir: str, **kwargs) -> EngineResult:
        start_time = time.time()
        model = kwargs.get("model") or settings.get("aider_model", "openrouter/deepseek/deepseek-chat")
        timeout = kwargs.get("timeout") or settings.get("timeout_seconds", 300)

        st_before = git_ops.get_status(project_dir)

        env = os.environ.copy()
        if OPENROUTER_API_KEY:
            env["OPENROUTER_API_KEY"] = OPENROUTER_API_KEY

        is_git = git_ops.is_git_repo(project_dir)
        cmd = [
            AIDER_BIN,
            "--model", model,
            "--message", prompt,
            "--yes-always",
            "--no-pretty",
            "--stream", "off"
        ]
        if not is_git:
            cmd.append("--no-git")

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=project_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
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
                engine=f"Aider ({model})",
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
                engine="Aider",
                prompt=prompt,
                duration=time.time() - start_time,
                error=f"Aider timed out after {timeout} seconds."
            )
        except Exception as e:
            return EngineResult(
                success=False,
                engine="Aider",
                prompt=prompt,
                duration=time.time() - start_time,
                error=f"Aider execution error: {str(e)}"
            )
