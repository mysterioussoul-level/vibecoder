"""
Comprehensive test suite for VibeCoder Autonomous Coding System.
"""

import os
import shutil
import pytest
import subprocess
from pathlib import Path

from vibecoder.config import settings, WORKSPACE_ROOT, PROJECTS_DIR
from vibecoder.core.project_manager import project_manager
from vibecoder.core.engine_manager import engine_manager
from vibecoder.core import git_ops, test_runner, shell_runner
from vibecoder.telegram_bot.ui import keyboards, formatters
from vibecoder.core.engines.base import EngineResult
from vibecoder.core.test_runner import TestReport

TEST_PROJECT_NAME = "test_vibe_unit_proj"
TEST_PROJECT_PATH = PROJECTS_DIR / TEST_PROJECT_NAME

@pytest.fixture(scope="session", autouse=True)
def setup_and_teardown():
    # Setup
    if TEST_PROJECT_PATH.exists():
        shutil.rmtree(TEST_PROJECT_PATH, ignore_errors=True)
    yield
    # Teardown
    if TEST_PROJECT_PATH.exists():
        shutil.rmtree(TEST_PROJECT_PATH, ignore_errors=True)

def test_settings_manager():
    orig = settings.get("default_engine")
    settings.set("default_engine", "antigravity")
    assert settings.get("default_engine") == "antigravity"
    
    settings.set("auto_test", True)
    assert settings.get("auto_test") is True

def test_project_scaffolding_and_git():
    ok, msg, p_path = project_manager.create_project(TEST_PROJECT_NAME, template="python")
    assert ok is True
    assert Path(p_path).exists()
    assert (Path(p_path) / "main.py").exists()
    assert (Path(p_path) / "tests" / "test_main.py").exists()

    # Verify Git initialization
    assert git_ops.is_git_repo(p_path) is True
    st = git_ops.get_status(p_path)
    assert st["clean"] is True
    assert st["branch"] in ("main", "master")

def test_project_switching_and_listing():
    projects = project_manager.list_projects()
    assert len(projects) > 0
    names = [p["name"] for p in projects]
    assert TEST_PROJECT_NAME in names

    ok, msg = project_manager.set_active_project(TEST_PROJECT_NAME)
    assert ok is True
    active = project_manager.get_active_project()
    assert active["name"] == TEST_PROJECT_NAME

def test_file_reading_and_security():
    ok, content = project_manager.read_file(str(TEST_PROJECT_PATH), "main.py")
    assert ok is True
    assert "FastAPI" in content

    # Traversal security check
    ok_hack, _ = project_manager.read_file(str(TEST_PROJECT_PATH), "../../../etc/passwd")
    assert ok_hack is False

def test_git_diff_and_revert():
    # Make a modification
    test_file = TEST_PROJECT_PATH / "main.py"
    original = test_file.read_text()
    test_file.write_text(original + "\n# Test vibe modification\n")

    st = git_ops.get_status(str(TEST_PROJECT_PATH))
    assert st["clean"] is False
    assert "main.py" in st["modified"]

    diff = git_ops.get_diff(str(TEST_PROJECT_PATH))
    assert "Test vibe modification" in diff

    # Revert
    ok, rev_msg = git_ops.revert_all(str(TEST_PROJECT_PATH))
    assert ok is True
    st_after = git_ops.get_status(str(TEST_PROJECT_PATH))
    assert st_after["clean"] is True

def test_automated_test_runner():
    rep = test_runner.run_project_tests(str(TEST_PROJECT_PATH))
    assert rep.passed is True
    assert rep.runner == "pytest"

@pytest.mark.asyncio
async def test_shell_runner():
    code, out, dur = await shell_runner.execute_shell("echo hello vibecoder", cwd=str(TEST_PROJECT_PATH))
    assert code == 0
    assert "hello vibecoder" in out

def test_engine_manager_registry():
    engines = engine_manager.list_engines()
    engine_ids = [e["id"] for e in engines]
    assert "antigravity" in engine_ids
    assert "aider" in engine_ids
    assert "copilot" in engine_ids
    assert "ensemble" in engine_ids

    engine = engine_manager.get_engine("antigravity")
    assert engine.name == "antigravity"

def test_telegram_formatters_and_escaping():
    proj = {"name": "test<proj>", "files_count": 5}
    git_st = {"branch": "main", "clean": True, "summary": "Clean <branch>"}
    card = formatters.format_dashboard(proj, "Antigravity & Gemini", git_st)
    assert "&lt;proj&gt;" in card
    assert "&amp;" in card

    # Test vibe result formatter with executed_commands and accomplishments
    from vibecoder.core.engines.antigravity_engine import format_tool_command
    assert format_tool_command("run_command", {"CommandLine": "pytest -v"}) == "$ pytest -v"
    assert format_tool_command("view_file", {"AbsolutePath": "/workspace/main.py"}) == "view_file (main.py)"
    assert format_tool_command("replace_file_content", {"TargetFile": "/workspace/cli.py"}) == "edit_file (cli.py)"

    res = EngineResult(
        success=True,
        engine="Antigravity (Gemini 3.8)",
        prompt="Build feature",
        output="Done <feature>",
        modified_files=["main.py"],
        diff_stat="1 file changed, 10 insertions(+)",
        test_report=TestReport(True, "pytest", "1 passed", "OK", 0.5),
        duration=1.2,
        executed_commands=["$ pytest -v", "view_file (main.py)", "edit_file (cli.py)"]
    )
    res_card = formatters.format_vibe_result(res)
    assert "𝗩𝗶𝗯𝗲 𝗖𝗼𝗱𝗶𝗻𝗴 𝗖𝗼𝗺𝗽𝗹𝗲𝘁𝗲!" in res_card
    assert "main.py" in res_card
    assert "&lt;feature&gt;" in res_card
    assert "📋 <b>What Was Accomplished:</b>" in res_card
    assert "💻 <b>Executed Commands:</b>" in res_card
    assert "view_file (main.py)" in res_card

def test_telegram_keyboards():
    main_kb = keyboards.main_menu_keyboard()
    assert len(main_kb.inline_keyboard) >= 5

    eng_kb = keyboards.engine_selection_keyboard(engine_manager.list_engines())
    assert len(eng_kb.inline_keyboard) >= 4

    vibe_kb = keyboards.vibe_result_keyboard()
    assert any(btn.callback_data == "session_reset" for row in vibe_kb.inline_keyboard for btn in row)

@pytest.mark.asyncio
async def test_conversation_caching_and_efficiency():
    from vibecoder.core.engines.antigravity_engine import AntigravityEngine
    eng = AntigravityEngine()
    test_dir = "/tmp/dummy_project"
    assert eng.get_conversation_id(test_dir) is None
    eng._conversations[test_dir] = "dummy-conv-1234"
    assert eng.get_conversation_id(test_dir) == "dummy-conv-1234"
    eng.reset_conversation(test_dir)
    assert eng.get_conversation_id(test_dir) is None

    # Test engine_manager reset
    engine_manager.reset_conversation()

    # Test async non-blocking test runner
    report = await test_runner.async_run_project_tests(str(TEST_PROJECT_PATH))
    assert report.passed is True

def test_transport_backup_script():
    transport_sh = WORKSPACE_ROOT / "transport.sh"
    assert transport_sh.exists()
    assert os.access(str(transport_sh), os.X_OK)

    # Test backup command
    proc = subprocess.run([str(transport_sh), "backup"], capture_output=True, text=True)
    assert proc.returncode == 0
    latest = WORKSPACE_ROOT / "vibecoder_backup_latest.tar.gz"
    assert latest.exists()
    assert latest.stat().st_size > 1000

@pytest.mark.asyncio
async def test_auth_manager():
    from vibecoder.core.auth_manager import auth_manager
    # Test openrouter auth check
    or_st = await auth_manager.check_openrouter_auth()
    assert or_st["authenticated"] is True
    assert "Free Tier" in or_st["details"]

    # Test auth keyboards
    auth_kb = keyboards.auth_menu_keyboard()
    assert len(auth_kb.inline_keyboard) >= 4
    device_kb = keyboards.copilot_device_keyboard("https://github.com/login/device")
    assert len(device_kb.inline_keyboard) >= 2

    # Test formatter
    st_dict = {
        "gemini": {"status": "Active 🟢", "details": "Ready"},
        "copilot": {"status": "Active 🟢", "details": "Auto mode"},
        "openrouter": {"status": "Active 🟢", "details": "Free Tier"}
    }
    card = formatters.format_auth_status(st_dict)
    assert "Active 🟢" in card
    assert "GitHub Copilot" in card
    assert "Google Antigravity" in card

    # Test token validation failure for empty input
    ok, err = await auth_manager.set_copilot_token("")
    assert ok is False
    ok_gem, err_gem = await auth_manager.set_gemini_auth("")
    assert ok_gem is False

def test_git_remote_and_github_sync():
    # Test setting and reading remote URL
    ok, msg = git_ops.set_remote_url(str(TEST_PROJECT_PATH), "https://github.com/mysterioussoul-level/test-repo.git")
    assert ok is True
    remote = git_ops.get_remote_url(str(TEST_PROJECT_PATH))
    assert remote == "https://github.com/mysterioussoul-level/test-repo.git"

    # Test git menu keyboard contains pull and publish buttons
    git_kb = keyboards.git_menu_keyboard()
    button_texts = [btn.text for row in git_kb.inline_keyboard for btn in row]
    assert any("Git Pull" in t for t in button_texts)
    assert any("Git Push" in t for t in button_texts)
    assert any("GitHub Publish" in t for t in button_texts)

@pytest.mark.asyncio
async def test_cloudflared_tunnel_manager():
    from vibecoder.core.tunnel_manager import tunnel_manager
    ports = tunnel_manager.get_active_ports()
    assert isinstance(ports, list)
    
    # Test PID checks
    assert tunnel_manager._is_pid_running(9999999) is False
    assert tunnel_manager._is_pid_running(os.getpid()) is True

    # Test formatter
    dummy_tunnels = [{
        "port": 8000,
        "url": "https://test-vibe.trycloudflare.com",
        "pid": 12345,
        "service": "FastAPI App",
        "started_at": 1000.0,
        "uptime": 120
    }]
    card = formatters.format_tunnels_view(dummy_tunnels, ports, "test_proj")
    assert "test-vibe.trycloudflare.com" in card
    assert "Port 8000" in card

    # Test keyboard
    kb = keyboards.tunnels_menu_keyboard(dummy_tunnels, ports)
    button_urls = [btn.url for row in kb.inline_keyboard for btn in row if btn.url]
    assert "https://test-vibe.trycloudflare.com" in button_urls
    button_callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row if btn.callback_data]
    assert "tunnel_stop:8000" in button_callbacks
    assert "tunnel_serve_project" in button_callbacks

