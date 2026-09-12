"""
Unified Engine Manager for VibeCoder.
Manages selection and execution across Antigravity, Aider, Copilot, and Ensemble engines.
"""

from typing import Dict, Any, List, Optional
from vibecoder.config import settings
from vibecoder.core.engines.base import BaseEngine, EngineResult
from vibecoder.core.engines.antigravity_engine import AntigravityEngine
from vibecoder.core.engines.aider_engine import AiderEngine
from vibecoder.core.engines.copilot_engine import CopilotEngine
from vibecoder.core.engines.ensemble_engine import EnsembleEngine

class EngineManager:
    """Registry and dispatcher for all AI coding engines."""

    def __init__(self):
        self._engines: Dict[str, BaseEngine] = {
            "antigravity": AntigravityEngine(),
            "aider": AiderEngine(),
            "copilot": CopilotEngine(),
            "ensemble": EnsembleEngine(),
        }

    def get_engine(self, name: Optional[str] = None) -> BaseEngine:
        target = name or settings.get("default_engine", "antigravity")
        engine = self._engines.get(target.lower())
        if not engine:
            engine = self._engines["antigravity"]
        return engine

    def set_default_engine(self, name: str) -> bool:
        if name.lower() in self._engines:
            settings.set("default_engine", name.lower())
            return True
        return False

    def list_engines(self) -> List[Dict[str, Any]]:
        current = settings.get("default_engine", "antigravity").lower()
        items = []
        for key, eng in self._engines.items():
            items.append({
                "id": key,
                "name": eng.name.capitalize(),
                "description": eng.description,
                "is_active": (key == current)
            })
        return items

    async def run_vibe(
        self,
        prompt: str,
        project_dir: Optional[str] = None,
        engine_name: Optional[str] = None,
        **kwargs
    ) -> EngineResult:
        """Execute a prompt with the chosen engine in the active project directory."""
        engine = self.get_engine(engine_name)
        target_dir = project_dir or settings.active_project
        return await engine.run(prompt=prompt, project_dir=target_dir, **kwargs)

engine_manager = EngineManager()
