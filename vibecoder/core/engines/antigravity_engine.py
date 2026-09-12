"""
Antigravity Engine implementation (Gemini 3.8 Flash).
Harnesses Google DeepMind Antigravity CLI for autonomous reasoning with real-time tool command streaming.
"""

import asyncio
import json
import os
import time
from typing import Optional, List, Dict, Any
from pathlib import Path

from vibecoder.config import AGY_BIN, settings
from vibecoder.core.engines.base import BaseEngine, EngineResult
from vibecoder.core import git_ops, test_runner
from vibecoder.core.shell_runner import strip_ansi

def format_tool_command(tool_name: str, params: Dict[str, Any]) -> str:
    """Format an agent tool call into a concise, human-readable terminal command."""
    if tool_name == "run_command":
        cmd = params.get("CommandLine") or params.get("command") or ""
        return f"$ {cmd}"[:55]
    elif tool_name in ("view_file", "read_file"):
        path = params.get("AbsolutePath") or params.get("TargetFile") or params.get("path") or ""
        return f"view_file ({Path(path).name})"
    elif tool_name in ("replace_file_content", "write_to_file", "multi_replace_file_content"):
        path = params.get("TargetFile") or params.get("path") or ""
        return f"edit_file ({Path(path).name})"
    elif tool_name in ("find_by_name", "grep_search"):
        pat = params.get("Pattern") or params.get("Query") or ""
        return f"{tool_name} ({pat})"[:55]
    elif tool_name == "list_dir":
        path = params.get("DirectoryPath") or params.get("path") or ""
        name = Path(path).name
        return f"list_dir ({name or '/'})"
    else:
        return f"tool: {tool_name}"

class AntigravityEngine(BaseEngine):
    """Antigravity CLI runner powered by Gemini 3.8 Flash."""

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
            "--output-format", "stream-json",
            "--dangerously-skip-permissions"
        ]

        executed_commands: List[str] = []
        final_summary: str = ""
        raw_outputs: List[str] = []

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=project_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=os.environ.copy()
            )

            async def stream_reader():
                nonlocal final_summary
                async for line in proc.stdout:
                    line_str = line.decode("utf-8", errors="replace").strip()
                    if not line_str:
                        continue
                    try:
                        ev = json.loads(line_str)
                        event_type = ev.get("event")
                        if event_type == "step_update":
                            su = ev.get("step_update", {})
                            step_type = su.get("step_type")
                            state = su.get("state")
                            if step_type == "tool" and state == "ACTIVE":
                                tool_name = su.get("tool_name", "tool")
                                params = su.get("tool_info", {}).get("parameters", {})
                                cmd_str = format_tool_command(tool_name, params)
                                executed_commands.append(cmd_str)
                                if on_progress:
                                    await on_progress(f"Running {tool_name}", cmd_str)
                            elif step_type == "agent_response" and state == "ACTIVE":
                                text_delta = su.get("text_delta", "")
                                if text_delta and "\n" in text_delta and on_progress:
                                    line_clean = text_delta.strip().split("\n")[0][:75]
                                    if len(line_clean) > 8:
                                        await on_progress("Formulating Code", line_clean)
                        elif event_type == "result":
                            res_obj = ev.get("result", {})
                            final_summary = res_obj.get("response", "").strip()
                    except Exception:
                        raw_outputs.append(line_str)

            reader_task = asyncio.create_task(stream_reader())
            _, stderr = await asyncio.wait_for(asyncio.gather(reader_task, proc.wait()), timeout=timeout)
            duration = time.time() - start_time
            success = (proc.returncode == 0)

            out_text = final_summary or "\n".join(raw_outputs).strip()
            out_text = strip_ansi(out_text)

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
                error="" if success else (out_text or "Process exited with non-zero status"),
                executed_commands=executed_commands
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
                error="" if has_working_code else f"Antigravity timed out after {timeout} seconds.",
                executed_commands=executed_commands
            )
        except Exception as e:
            return EngineResult(
                success=False,
                engine="Antigravity",
                prompt=prompt,
                duration=time.time() - start_time,
                error=f"Antigravity execution error: {str(e)}",
                executed_commands=executed_commands
            )
