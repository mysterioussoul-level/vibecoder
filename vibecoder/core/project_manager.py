"""
Project & Workspace Manager for Autonomous Vibe Coding System.
Handles project switching, template scaffolding, git cloning, and file browsing.
"""

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

from vibecoder.config import PROJECTS_DIR, WORKSPACE_ROOT, settings, GH_BIN, GIT_BIN
from vibecoder.core import git_ops

TEMPLATES = {
    "python": {
        "description": "FastAPI Web API with pytest",
        "files": {
            "main.py": """from fastapi import FastAPI

app = FastAPI(title="Vibe App")

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Vibe coding active!"}

@app.get("/health")
def health():
    return {"healthy": True}
""",
            "requirements.txt": """fastapi>=0.100.0
uvicorn>=0.23.0
pytest>=8.0.0
httpx>=0.27.0
""",
            "tests/__init__.py": "",
            "tests/test_main.py": """from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
""",
            ".gitignore": """__pycache__/
*.py[cod]
*$py.class
.venv/
venv/
.env
.pytest_cache/
""",
            "README.md": """# VibeCoder Project

Built with Autonomous Vibe Coding.
"""
        }
    },
    "cli": {
        "description": "Python CLI Application with argparse",
        "files": {
            "cli.py": """import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="Vibe CLI Tool")
    parser.add_argument("--name", default="World", help="Name to greet")
    args = parser.parse_args()
    print(f"Hello, {args.name} from VibeCoder!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
""",
            "test_cli.py": """import subprocess
import sys

def test_cli_execution():
    proc = subprocess.run([sys.executable, "cli.py", "--name", "Tester"], capture_output=True, text=True)
    assert proc.returncode == 0
    assert "Tester" in proc.stdout
""",
            ".gitignore": """__pycache__/
*.pyc
.pytest_cache/
""",
            "README.md": """# Vibe CLI

Run: `python3 cli.py`
"""
        }
    },
    "node": {
        "description": "Node.js Express Server",
        "files": {
            "index.js": """const express = require('express');
const app = express();
const port = process.env.PORT || 3000;

app.use(express.json());

app.get('/', (req, res) => {
    res.json({ message: 'Welcome to Vibe Node API' });
});

if (require.main === module) {
    app.listen(port, () => console.log(`Server listening on port ${port}`));
}

module.exports = app;
""",
            "package.json": """{
  "name": "vibe-node-app",
  "version": "1.0.0",
  "main": "index.js",
  "scripts": {
    "start": "node index.js",
    "test": "node --check index.js"
  },
  "dependencies": {
    "express": "^4.19.2"
  }
}
""",
            ".gitignore": """node_modules/
.env
*.log
""",
            "README.md": """# Vibe Node App

Run: `npm install && npm start`
"""
        }
    },
    "web": {
        "description": "Modern HTML5 / CSS / Vanilla JS Web App",
        "files": {
            "index.html": """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vibe Studio App</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container">
        <h1>✨ Vibe Studio</h1>
        <p id="msg">Autonomous vibe coding system active.</p>
        <button id="btn" class="glow-button">Click Me</button>
    </div>
    <script src="app.js"></script>
</body>
</html>
""",
            "style.css": """body {
    margin: 0;
    font-family: system-ui, -apple-system, sans-serif;
    background: #0f172a;
    color: #f8fafc;
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
}
.container {
    text-align: center;
    background: #1e293b;
    padding: 2.5rem;
    border-radius: 16px;
    box-shadow: 0 10px 25px -5px rgba(0,0,0,0.5);
}
.glow-button {
    background: linear-gradient(135deg, #6366f1, #a855f7);
    color: white;
    border: none;
    padding: 12px 24px;
    font-size: 1rem;
    font-weight: 600;
    border-radius: 8px;
    cursor: pointer;
    transition: transform 0.2s, box-shadow 0.2s;
}
.glow-button:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 15px rgba(168, 85, 247, 0.4);
}
""",
            "app.js": """document.getElementById('btn').addEventListener('click', () => {
    document.getElementById('msg').innerText = '🚀 Vibe Coding in real-time!';
});
""",
            "README.md": """# Modern Web App

Open `index.html` in browser.
"""
        }
    },
    "blank": {
        "description": "Empty project with Git and README",
        "files": {
            "README.md": """# New Vibe Project

Ready for autonomous coding!
""",
            ".gitignore": """# Gitignore
.env
__pycache__/
node_modules/
"""
        }
    }
}

class ProjectManager:
    """Manages multi-project workspace switching and lifecycle."""

    def __init__(self):
        PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

    def list_projects(self) -> List[Dict[str, Any]]:
        """List all managed projects plus recognized root repositories."""
        projects = []
        active_path = str(Path(settings.active_project).resolve())

        # Check projects directory
        if PROJECTS_DIR.exists():
            for p in sorted(PROJECTS_DIR.iterdir()):
                if p.is_dir() and not p.name.startswith("."):
                    projects.append(self._get_project_summary(p, active_path))

        # Check existing root directories if they look like projects
        root_candidates = [WORKSPACE_ROOT / "mirror-leech-telegram-bot"]
        for p in root_candidates:
            if p.exists() and p.is_dir() and not any(proj["path"] == str(p.resolve()) for proj in projects):
                projects.append(self._get_project_summary(p, active_path))

        # If still empty, add workspace root itself
        if not projects:
            projects.append(self._get_project_summary(WORKSPACE_ROOT, active_path))

        return projects

    def _get_project_summary(self, path: Path, active_path: str) -> Dict[str, Any]:
        p_res = path.resolve()
        is_active = (str(p_res) == active_path)
        git_st = git_ops.get_status(str(p_res))

        file_count = 0
        try:
            for item in p_res.rglob("*"):
                if item.is_file() and not any(part.startswith(".") for part in item.parts):
                    file_count += 1
                    if file_count > 500:
                        break
        except Exception:
            pass

        return {
            "name": path.name,
            "path": str(p_res),
            "is_active": is_active,
            "is_git": git_st["is_git"],
            "branch": git_st["branch"],
            "clean": git_st["clean"],
            "status_summary": git_st["summary"],
            "files_count": file_count,
        }

    def get_active_project(self) -> Dict[str, Any]:
        active_path = Path(settings.active_project).resolve()
        if not active_path.exists():
            active_path = PROJECTS_DIR
            settings.set_active_project(str(active_path))
        return self._get_project_summary(active_path, str(active_path))

    def set_active_project(self, name_or_path: str) -> Tuple[bool, str]:
        p = Path(name_or_path).resolve()
        if p.exists() and p.is_dir():
            settings.set_active_project(str(p))
            return True, f"Switched to project: {p.name}"

        sub = PROJECTS_DIR / name_or_path
        if sub.exists() and sub.is_dir():
            settings.set_active_project(str(sub.resolve()))
            return True, f"Switched to project: {sub.name}"

        sub_root = WORKSPACE_ROOT / name_or_path
        if sub_root.exists() and sub_root.is_dir():
            settings.set_active_project(str(sub_root.resolve()))
            return True, f"Switched to project: {sub_root.name}"

        return False, f"Project '{name_or_path}' not found."

    def create_project(self, name: str, template: str = "python") -> Tuple[bool, str, str]:
        """Create a new project from template and initialize git."""
        clean_name = "".join(c for c in name if c.isalnum() or c in ("-", "_")).strip()
        if not clean_name:
            return False, "Invalid project name. Use letters, numbers, hyphens.", ""

        target_dir = PROJECTS_DIR / clean_name
        if target_dir.exists():
            return False, f"Project '{clean_name}' already exists.", str(target_dir)

        target_dir.mkdir(parents=True, exist_ok=True)
        tmpl = TEMPLATES.get(template, TEMPLATES["python"])

        # Write files
        for rel_file, file_content in tmpl["files"].items():
            f_path = target_dir / rel_file
            f_path.parent.mkdir(parents=True, exist_ok=True)
            f_path.write_text(file_content, encoding="utf-8")

        # Init git repo and commit
        git_ops.init_repo(str(target_dir))
        git_ops.commit_all(str(target_dir), f"Initial scaffold: {template} template via VibeCoder")

        # Set as active
        settings.set_active_project(str(target_dir))
        return True, f"Created new {template} project '{clean_name}'!", str(target_dir)

    def clone_repo(self, url: str, custom_name: Optional[str] = None) -> Tuple[bool, str, str]:
        """Clone a remote git repository and set it as active."""
        url = url.strip()
        if not url:
            return False, "Repository URL cannot be empty.", ""

        if not custom_name:
            clean_url = url.rstrip("/").rstrip(".git")
            custom_name = clean_url.split("/")[-1]
            if not custom_name:
                custom_name = f"repo_{int(time.time())}"

        target_dir = PROJECTS_DIR / custom_name
        if target_dir.exists():
            settings.set_active_project(str(target_dir))
            return True, f"Repository already exists. Switched active project to '{custom_name}'.", str(target_dir)

        try:
            proc = subprocess.run(
                [GIT_BIN, "clone", "--depth", "1", url, str(target_dir)],
                capture_output=True,
                text=True,
                timeout=120,
                check=False
            )
            if proc.returncode == 0:
                settings.set_active_project(str(target_dir))
                return True, f"Successfully cloned '{custom_name}' and set as active!", str(target_dir)
            return False, f"Clone failed: {proc.stderr or proc.stdout}", ""
        except Exception as e:
            return False, f"Error cloning repository: {str(e)}", ""

    def get_file_tree(self, project_path: str, max_depth: int = 2) -> List[Dict[str, Any]]:
        """List files and folders in project hierarchy."""
        base = Path(project_path).resolve()
        if not base.exists():
            return []

        entries = []
        try:
            for item in sorted(base.rglob("*")):
                rel = item.relative_to(base)
                if any(p.startswith(".") or p in ("node_modules", "__pycache__", "venv", ".venv") for p in rel.parts):
                    continue
                if len(rel.parts) > max_depth:
                    continue

                entries.append({
                    "name": item.name,
                    "rel_path": str(rel),
                    "is_dir": item.is_dir(),
                    "size": item.stat().st_size if item.is_file() else 0,
                    "depth": len(rel.parts)
                })
        except Exception:
            pass

        return entries

    def read_file(self, project_path: str, rel_path: str, max_bytes: int = 20000) -> Tuple[bool, str]:
        """Read content of a project file."""
        base = Path(project_path).resolve()
        target = (base / rel_path).resolve()

        if not str(target).startswith(str(base)):
            return False, "Access denied: Path outside project."

        if not target.exists() or not target.is_file():
            return False, f"File '{rel_path}' not found."

        try:
            raw = target.read_bytes()
            if len(raw) > max_bytes:
                content = raw[:max_bytes].decode("utf-8", errors="replace")
                content += f"\n\n... [Truncated: file is {len(raw)} bytes]"
            else:
                content = raw.decode("utf-8", errors="replace")
            return True, content
        except Exception as e:
            return False, f"Error reading file: {str(e)}"

project_manager = ProjectManager()
