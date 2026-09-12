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
from vibecoder.core import git_ops, test_runner

class EnsembleEngine(BaseEngine):
    """Ensemble orchestrator with self-healing feedback loop."""

    def __init__(self):
        self.antigravity = AntigravityEngine()

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

        while iteration < max_iters:
            iteration += 1
            res = await self.antigravity.run(current_prompt, project_dir, timeout=timeout)
            last_result = res

            if not res.success:
                break

            test_rep = test_runner.run_project_tests(project_dir)
            res.test_report = test_rep

            if test_rep.passed:
                break

            if iteration < max_iters:
                current_prompt = (
                    f"Test/Syntax Verification FAILED on iteration {iteration}.\n"
                    f"Runner: {test_rep.runner}\n"
                    f"Summary: {test_rep.summary}\n"
                    f"Error Output:\n{test_rep.output[:1500]}\n\n"
                    "Please diagnose and fix the failing code in the project files immediately."
                )

        duration = time.time() - start_time
        if last_result:
            last_result.engine = f"Auto Vibe ({iteration} iter{'s' if iteration > 1 else ''})"
            last_result.duration = duration
            return last_result

        return EngineResult(
            success=False,
            engine="Auto Vibe",
            prompt=prompt,
            duration=duration,
            error="Ensemble execution failed to run."
        )
