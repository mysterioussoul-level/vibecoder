"""
Ensemble / Auto Vibe Engine.
Autonomous self-healing loop:
Plan & Execute -> Test & Verify -> Auto-Heal / Refine -> Final Report.
"""

import asyncio
import time
from typing import Optional

from vibecoder.config import settings
from vibecoder.core.engines.base import BaseEngine, EngineResult
from vibecoder.core.engines.antigravity_engine import AntigravityEngine
from vibecoder.core.engines.copilot_engine import CopilotEngine
from vibecoder.core.engines.aider_engine import AiderEngine
from vibecoder.core import git_ops, test_runner

class EnsembleEngine(BaseEngine):
    """Ensemble orchestrator with self-healing feedback loop across AI engines."""

    def __init__(self):
        self.antigravity = AntigravityEngine()
        self.copilot = CopilotEngine()
        self.aider = AiderEngine()

    @property
    def name(self) -> str:
        return "ensemble"

    @property
    def description(self) -> str:
        return "Auto Vibe (Plan + Gemini 3.8 Code + Auto-Verification + Self-Healing)"

    async def run(self, prompt: str, project_dir: str, **kwargs) -> EngineResult:
        start_time = time.time()
        max_iters = kwargs.get("max_iterations") or settings.get("max_iterations", 2)
        timeout = kwargs.get("timeout") or settings.get("timeout_seconds", 300)
        on_progress = kwargs.get("on_progress")

        vibe_prompt = (
            f"User Vibe Request: {prompt}\n\n"
            "Autonomous Guidelines:\n"
            "1. Inspect the workspace files and project context.\n"
            "2. Implement high-quality, clean, production-ready code fulfilling the request.\n"
            "3. Ensure all imports, syntax, types, and unit tests (if applicable) are valid.\n"
            "4. Provide a concise summary of changes made."
        )

        current_prompt = vibe_prompt
        iteration = 0
        last_result: Optional[EngineResult] = None
        used_engines = []

        while iteration < max_iters:
            iteration += 1

            # Step 1: Execute with Gemini 3.8 / Antigravity
            if on_progress:
                await on_progress("Gemini 3.8", f"Architecting solution & generating code (iteration {iteration}/{max_iters})...")

            res = await self.antigravity.run(current_prompt, project_dir, timeout=timeout, **kwargs)
            used_engines.append("Gemini 3.8")

            # If Antigravity failed or made no changes, fallback to GitHub Copilot
            if not res.success or not res.modified_files:
                if on_progress:
                    await on_progress("Copilot Fallback", "Antigravity did not modify files; delegating to Copilot CLI...")
                copilot_res = await self.copilot.run(current_prompt, project_dir, timeout=timeout, **kwargs)
                used_engines.append("Copilot")
                if copilot_res.success and copilot_res.modified_files:
                    res = copilot_res
                elif not copilot_res.modified_files and settings.get("OPENROUTER_API_KEY"):
                    if on_progress:
                        await on_progress("Aider Fallback", "Delegating to Aider for AST-based code edits...")
                    aider_res = await self.aider.run(current_prompt, project_dir, timeout=timeout, **kwargs)
                    used_engines.append("Aider")
                    if aider_res.success and aider_res.modified_files:
                        res = aider_res

            last_result = res

            # Step 2: Automated Test Verification
            if on_progress:
                await on_progress("Testing", "Executing automated test suite (pytest/npm/syntax check)...")

            test_rep = test_runner.run_project_tests(project_dir)
            res.test_report = test_rep

            if test_rep.passed:
                res.success = True
                break

            # Step 3: Self-Healing on Test Failure
            if iteration < max_iters:
                if on_progress:
                    await on_progress("Self-Healing", f"Tests failed ({test_rep.summary}); formulating patch...")
                current_prompt = (
                    f"Test/Syntax Verification FAILED on iteration {iteration}.\n"
                    f"Runner: {test_rep.runner}\n"
                    f"Summary: {test_rep.summary}\n"
                    f"Error Output:\n{test_rep.output[:1500]}\n\n"
                    "Please diagnose and fix the failing code in the project files immediately."
                )
            else:
                # Max iterations reached and tests still failing
                res.success = False
                res.error = f"Automated tests failed ({test_rep.summary}):\n{test_rep.output[:800]}"

        duration = time.time() - start_time
        if last_result:
            engine_summary = " + ".join(dict.fromkeys(used_engines)) or "Auto Vibe"
            last_result.engine = f"{engine_summary} ({iteration} iter{'s' if iteration > 1 else ''})"
            last_result.duration = duration
            return last_result

        return EngineResult(
            success=False,
            engine="Auto Vibe",
            prompt=prompt,
            duration=duration,
            error="Ensemble execution failed to generate code."
        )
