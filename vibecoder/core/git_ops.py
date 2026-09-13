"""
Git operations for Autonomous Vibe Coding System.
Provides status inspection, diff generation, commits, push, and rollback.
"""

import subprocess
import os
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from vibecoder.config import GIT_BIN, GH_BIN

def run_git_cmd(args: List[str], cwd: str, timeout: int = 30) -> Tuple[int, str, str]:
    """Execute a git command in cwd safely."""
    try:
        proc = subprocess.run(
            [GIT_BIN] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False
        )
        return proc.returncode, proc.stdout.rstrip("\r\n"), proc.stderr.rstrip("\r\n")
    except subprocess.TimeoutExpired:
        return -1, "", f"Git command timed out after {timeout}s"
    except Exception as e:
        return -1, "", str(e)

def is_git_repo(path: str) -> bool:
    """Check if the directory is a git repository itself."""
    p = Path(path).resolve()
    if (p / ".git").exists():
        return True
    ret, out, _ = run_git_cmd(["rev-parse", "--show-toplevel"], cwd=str(p))
    if ret == 0 and out:
        return Path(out).resolve() == p
    return False

def init_repo(path: str) -> Tuple[bool, str]:
    """Initialize a git repository if not already one."""
    if is_git_repo(path):
        return True, "Already a git repository"
    ret, out, err = run_git_cmd(["init"], cwd=path)
    if ret == 0:
        run_git_cmd(["config", "user.name", "VibeCoder Autonomous"], cwd=path)
        run_git_cmd(["config", "user.email", "vibecoder@local.dev"], cwd=path)
        return True, "Initialized git repository"
    return False, err or out

def get_current_branch(path: str) -> str:
    """Get active git branch name."""
    if not is_git_repo(path):
        return "not a git repo"
    ret, out, _ = run_git_cmd(["branch", "--show-current"], cwd=path)
    if ret == 0 and out:
        return out
    ret, out, _ = run_git_cmd(["symbolic-ref", "--short", "HEAD"], cwd=path)
    return out if ret == 0 and out else "main"

def get_status(path: str) -> Dict[str, Any]:
    """Inspect working tree status."""
    if not is_git_repo(path):
        return {
            "is_git": False,
            "branch": "none",
            "clean": True,
            "modified": [],
            "untracked": [],
            "staged": [],
            "summary": "Not a git repository"
        }

    # Single git command fetching branch header and status changes together
    ret, out, _ = run_git_cmd(["status", "-b", "--porcelain"], cwd=path)

    branch = "main"
    lines = out.splitlines() if (ret == 0 and out) else []
    if lines and lines[0].startswith("## "):
        b_header = lines[0][3:].strip()
        branch = b_header.split("...")[0].strip()
        lines = lines[1:]
    elif ret != 0:
        branch = get_current_branch(path)

    modified = []
    untracked = []
    staged = []

    for line in lines:
        line = line.rstrip()
        if len(line) < 3:
            continue
        index_code = line[0]
        worktree_code = line[1]
        fname = line[2:].strip()
        if " -> " in fname:
            fname = fname.split(" -> ")[1].strip()
        if index_code in ("M", "A", "D", "R"):
            staged.append(fname)
        if worktree_code == "M":
            modified.append(fname)
        elif index_code == "?" and worktree_code == "?":
            untracked.append(fname)
        elif worktree_code == "D":
            modified.append(f"{fname} (deleted)")

    all_changes = list(dict.fromkeys(modified + untracked + staged))
    clean = len(all_changes) == 0

    if clean:
        summary = f"Branch '{branch}' is clean."
    else:
        parts = []
        if modified:
            parts.append(f"{len(modified)} modified")
        if untracked:
            parts.append(f"{len(untracked)} untracked")
        if staged:
            parts.append(f"{len(staged)} staged")
        summary = f"Branch '{branch}': " + ", ".join(parts)

    return {
        "is_git": True,
        "branch": branch,
        "clean": clean,
        "modified": modified,
        "untracked": untracked,
        "staged": staged,
        "all_changes": all_changes,
        "summary": summary
    }

def get_diff(path: str, max_lines: int = 150) -> str:
    """Get git diff for modified files."""
    if not is_git_repo(path):
        return "Not a git repository."

    ret1, out1, _ = run_git_cmd(["diff"], cwd=path)
    ret2, out2, _ = run_git_cmd(["diff", "--cached"], cwd=path)

    diff_parts = []
    if out2:
        diff_parts.append("# Staged changes:\n" + out2)
    if out1:
        diff_parts.append("# Unstaged changes:\n" + out1)

    full_diff = "\n".join(diff_parts).strip()
    if not full_diff:
        st = get_status(path)
        if st["untracked"]:
            return "No modifications to tracked files, but untracked files exist:\n" + "\n".join(f"+ {f}" for f in st["untracked"])
        return "No changes detected."

    lines = full_diff.splitlines()
    if len(lines) > max_lines:
        truncated = "\n".join(lines[:max_lines])
        truncated += f"\n\n... [Truncated: showing first {max_lines} of {len(lines)} lines]"
        return truncated
    return full_diff

def get_diff_stat(path: str) -> str:
    """Get concise diff statistics."""
    if not is_git_repo(path):
        return ""
    ret, out, _ = run_git_cmd(["diff", "HEAD", "--stat"], cwd=path)
    if ret != 0 or not out:
        ret, out, _ = run_git_cmd(["diff", "--stat"], cwd=path)
    return out.strip() if ret == 0 else ""

def commit_all(path: str, message: str) -> Tuple[bool, str]:
    """Stage all changes and create a git commit."""
    if not is_git_repo(path):
        init_repo(path)

    run_git_cmd(["config", "user.name", "VibeCoder Autonomous"], cwd=path)
    run_git_cmd(["config", "user.email", "vibecoder@local.dev"], cwd=path)

    ret, out, err = run_git_cmd(["add", "-A"], cwd=path)
    if ret != 0:
        return False, f"Failed to stage changes: {err or out}"

    ret, out, err = run_git_cmd(["commit", "-m", message], cwd=path)
    if ret != 0:
        if "nothing to commit" in (out + err):
            return True, "Nothing to commit, working tree clean."
        return False, f"Commit failed: {err or out}"

    return True, out

def push(path: str, remote: str = "origin", branch: Optional[str] = None) -> Tuple[bool, str]:
    """Push commits to remote."""
    if not is_git_repo(path):
        return False, "Not a git repository."
    if not branch:
        branch = get_current_branch(path)

    ret, out, err = run_git_cmd(["push", remote, branch], cwd=path, timeout=60)
    if ret == 0:
        return True, out or f"Pushed to {remote}/{branch}"
    return False, err or out

def revert_all(path: str) -> Tuple[bool, str]:
    """Revert all working directory changes to HEAD."""
    if not is_git_repo(path):
        return False, "Not a git repository."

    run_git_cmd(["reset", "--hard", "HEAD"], cwd=path)
    ret, out, err = run_git_cmd(["clean", "-fd"], cwd=path)
    if ret == 0:
        return True, "Successfully reverted all changes to HEAD."
    return False, err or out

def get_recent_commits(path: str, count: int = 5) -> List[Dict[str, str]]:
    """Retrieve list of recent commit messages and hashes."""
    if not is_git_repo(path):
        return []
    ret, out, _ = run_git_cmd(["log", f"-n{count}", "--pretty=format:%h|%an|%ar|%s"], cwd=path)
    if ret != 0 or not out:
        return []

    commits = []
    for line in out.splitlines():
        parts = line.split("|", 3)
        if len(parts) == 4:
            commits.append({
                "hash": parts[0],
                "author": parts[1],
                "time": parts[2],
                "message": parts[3]
            })
    return commits
 
def pull(path: str, remote: str = "origin", branch: Optional[str] = None) -> Tuple[bool, str]:
    """Pull latest updates from remote GitHub repository."""
    if not is_git_repo(path):
        return False, "Not a git repository."
    if not branch:
        branch = get_current_branch(path)

    ret, out, err = run_git_cmd(["pull", remote, branch], cwd=path, timeout=60)
    if ret == 0:
        return True, out or f"Successfully pulled latest updates from {remote}/{branch}"
    return False, err or out

def get_remote_url(path: str, remote: str = "origin") -> Optional[str]:
    """Get remote URL for repository."""
    if not is_git_repo(path):
        return None
    ret, out, _ = run_git_cmd(["remote", "get-url", remote], cwd=path)
    if ret == 0 and out:
        return out.strip()
    return None

def set_remote_url(path: str, url: str, remote: str = "origin") -> Tuple[bool, str]:
    """Set or add remote URL for repository."""
    if not is_git_repo(path):
        init_repo(path)
    existing = get_remote_url(path, remote)
    if existing:
        ret, out, err = run_git_cmd(["remote", "set-url", remote, url], cwd=path)
    else:
        ret, out, err = run_git_cmd(["remote", "add", remote, url], cwd=path)
    if ret == 0:
        return True, f"Remote '{remote}' set to {url}"
    return False, err or out

def publish_to_github(path: str, repo_name: Optional[str] = None, private: bool = True) -> Tuple[bool, str]:
    """Publish repository to GitHub using GitHub CLI (gh)."""
    if not is_git_repo(path):
        init_repo(path)
    p = Path(path).resolve()
    name = repo_name or p.name

    # Ensure at least one commit exists
    commit_all(path, f"Initial commit for {name} via VibeCoder")

    existing_remote = get_remote_url(path, "origin")
    if existing_remote:
        # Already linked to remote, push latest
        succ, out = push(path, "origin")
        if succ:
            return True, f"Repository already connected to {existing_remote}.\nSuccessfully pushed latest code!"
        return False, f"Remote exists ({existing_remote}), but push failed: {out}"

    vis = "--private" if private else "--public"
    try:
        proc = subprocess.run(
            [GH_BIN, "repo", "create", name, vis, "--source=.", "--remote=origin", "--push"],
            cwd=str(p),
            capture_output=True,
            text=True,
            timeout=60,
            check=False
        )
        if proc.returncode == 0:
            remote_url = get_remote_url(path, "origin") or f"https://github.com/{name}"
            return True, f"Successfully created & pushed to GitHub:\n{remote_url}"
        return False, proc.stderr or proc.stdout
    except Exception as e:
        return False, f"Failed executing gh CLI: {str(e)}"
