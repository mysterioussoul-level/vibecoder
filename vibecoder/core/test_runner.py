"""
Automated test runner and syntax verifier for VibeCoder.
Detects project ecosystem and validates changes automatically.
"""

import subprocess
import time
import os
from pathlib import Path
from typing import Dict, Any, Optional

class TestReport:
    __test__ = False
    def __init__(self, passed: bool, runner: str, summary: str, output: str, duration: float):
        self.passed = passed
        self.runner = runner
        self.summary = summary
        self.output = output
        self.duration = duration

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "runner": self.runner,
            "summary": self.summary,
            "output": self.output,
            "duration": round(self.duration, 2),
        }

def run_cmd(cmd: list, cwd: str, timeout: int = 60) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        out = (proc.stdout + "\n" + proc.stderr).strip()
        return proc.returncode, out
    except subprocess.TimeoutExpired:
        return -1, f"Execution timed out after {timeout}s"
    except Exception as e:
        return -1, str(e)

def run_project_tests(project_path: str, timeout: int = 90) -> TestReport:
    p = Path(project_path).resolve()
    start_time = time.time()

    has_py_files = any(p.glob("*.py")) or any(p.glob("*/*.py"))
    has_pytest = any(p.glob("test_*.py")) or any(p.glob("*/**/test_*.py")) or (p / "tests").is_dir()
    
    if (p / "package.json").exists():
        pkg_json = (p / "package.json").read_text(encoding="utf-8", errors="ignore")
        if '"test"' in pkg_json:
            code, out = run_cmd(["npm", "test"], cwd=str(p), timeout=timeout)
            dur = time.time() - start_time
            passed = (code == 0)
            summary = "All tests passed" if passed else "npm test failed"
            return TestReport(passed=passed, runner="npm test", summary=summary, output=out[:2000], duration=dur)

    if (p / "Cargo.toml").exists():
        code, out = run_cmd(["cargo", "test"], cwd=str(p), timeout=timeout)
        dur = time.time() - start_time
        passed = (code == 0)
        summary = "Cargo tests passed" if passed else "Cargo test failed"
        return TestReport(passed=passed, runner="cargo test", summary=summary, output=out[:2000], duration=dur)

    if (p / "go.mod").exists():
        code, out = run_cmd(["go", "test", "./..."], cwd=str(p), timeout=timeout)
        dur = time.time() - start_time
        passed = (code == 0)
        summary = "Go tests passed" if passed else "Go test failed"
        return TestReport(passed=passed, runner="go test", summary=summary, output=out[:2000], duration=dur)

    if has_pytest:
        code, out = run_cmd(["python3", "-m", "pytest", "-q"], cwd=str(p), timeout=timeout)
        dur = time.time() - start_time
        passed = (code == 0)
        lines = out.splitlines()
        last_line = lines[-1] if lines else ("Passed" if passed else "Failed")
        return TestReport(passed=passed, runner="pytest", summary=last_line, output=out[:2000], duration=dur)

    if has_py_files:
        failed_files = []
        errors = []
        for py_file in p.rglob("*.py"):
            if ".venv" in py_file.parts or "node_modules" in py_file.parts or "__pycache__" in py_file.parts:
                continue
            code, out = run_cmd(["python3", "-m", "py_compile", str(py_file)], cwd=str(p), timeout=10)
            if code != 0:
                failed_files.append(str(py_file.relative_to(p)))
                errors.append(out)

        dur = time.time() - start_time
        if failed_files:
            return TestReport(
                passed=False,
                runner="py_compile",
                summary=f"Syntax error in {len(failed_files)} file(s): {', '.join(failed_files[:3])}",
                output="\n".join(errors)[:2000],
                duration=dur
            )
        return TestReport(
            passed=True,
            runner="py_compile",
            summary="Python syntax validation clean (no tests defined).",
            output="All .py files compiled cleanly without syntax errors.",
            duration=dur
        )

    dur = time.time() - start_time
    return TestReport(
        passed=True,
        runner="none",
        summary="No automated test suite detected.",
        output="Workspace has no test suite configured.",
        duration=dur
    )
