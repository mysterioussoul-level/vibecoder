"""
Base Engine interface and data classes for VibeCoder AI engines.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from vibecoder.core.test_runner import TestReport

class EngineResult:
    """Standardized result returned by all coding engines."""
    def __init__(
        self,
        success: bool,
        engine: str,
        prompt: str,
        output: str = "",
        modified_files: Optional[List[str]] = None,
        diff_stat: str = "",
        test_report: Optional[TestReport] = None,
        duration: float = 0.0,
        error: str = ""
    ):
        self.success = success
        self.engine = engine
        self.prompt = prompt
        self.output = output
        self.modified_files = modified_files or []
        self.diff_stat = diff_stat
        self.test_report = test_report
        self.duration = duration
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "engine": self.engine,
            "prompt": self.prompt,
            "output": self.output[:4000],
            "modified_files": self.modified_files,
            "diff_stat": self.diff_stat,
            "test_report": self.test_report.to_dict() if self.test_report else None,
            "duration": round(self.duration, 2),
            "error": self.error,
        }

class BaseEngine(ABC):
    """Abstract interface for autonomous coding engines."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @abstractmethod
    async def run(self, prompt: str, project_dir: str, **kwargs) -> EngineResult:
        pass
