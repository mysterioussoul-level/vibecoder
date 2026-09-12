"""
Interactive CLI interface for VibeCoder.
Allows vibe coding, project management, and engine testing directly in the terminal.
"""

import asyncio
import sys
from vibecoder.config import settings
from vibecoder.core.project_manager import project_manager
from vibecoder.core.engine_manager import engine_manager
from vibecoder.core import git_ops, test_runner

async def main():
    print("=" * 65)
    print("✨ VIBECODER • AUTONOMOUS VIBE CODING CLI")
    print("=" * 65)

    proj = project_manager.get_active_project()
    engine = engine_manager.get_engine()

    print(f"📂 Active Project: {proj['name']} ({proj['path']})")
    print(f"🌿 Git Branch:    {proj['branch']}")
    print(f"🤖 AI Engine:     {engine.description}")
    print("-" * 65)
    print("Commands:")
    print("  /engine <name>         - Switch engine (antigravity, aider, copilot, ensemble)")
    print("  /project <name|path>   - Switch project")
    print("  /new <name> [tmpl]     - Create new project (python, cli, node, web, blank)")
    print("  /clone <repo_url>      - Clone git repository")
    print("  /diff                  - View git diff")
    print("  /test                  - Run automated tests")
    print("  /commit <msg>          - Git commit changes")
    print("  /exit                  - Quit CLI")
    print("  <any prompt>           - Execute vibe coding autonomously!")
    print("=" * 65)

    while True:
        try:
            prompt = input("\n👉 Vibe Prompt > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting VibeCoder CLI.")
            break

        if not prompt:
            continue

        if prompt == "/exit":
            break

        if prompt.startswith("/engine"):
            parts = prompt.split()
            if len(parts) > 1:
                if engine_manager.set_default_engine(parts[1]):
                    print(f"✓ Engine switched to: {parts[1]}")
                else:
                    print(f"✗ Unknown engine. Available: {', '.join(e['id'] for e in engine_manager.list_engines())}")
            else:
                print("Available engines:")
                for e in engine_manager.list_engines():
                    mark = "✅ " if e["is_active"] else "   "
                    print(f"  {mark}{e['name']}: {e['description']}")
            continue

        if prompt.startswith("/project"):
            parts = prompt.split(maxsplit=1)
            if len(parts) > 1:
                ok, msg = project_manager.set_active_project(parts[1])
                print(msg)
            else:
                print("Available projects:")
                for p in project_manager.list_projects():
                    mark = "✅ " if p["is_active"] else "   "
                    print(f"  {mark}{p['name']} ({p['branch']})")
            continue

        if prompt.startswith("/new"):
            parts = prompt.split()
            if len(parts) > 1:
                name = parts[1]
                tmpl = parts[2] if len(parts) > 2 else "python"
                ok, msg, path = project_manager.create_project(name, tmpl)
                print(msg)
            else:
                print("Usage: /new <name> [template: python|cli|node|web|blank]")
            continue

        if prompt.startswith("/clone"):
            parts = prompt.split()
            if len(parts) > 1:
                ok, msg, path = project_manager.clone_repo(parts[1])
                print(msg)
            else:
                print("Usage: /clone <repo_url>")
            continue

        if prompt == "/diff":
            active_p = project_manager.get_active_project()
            print(git_ops.get_diff(active_p["path"]))
            continue

        if prompt == "/test":
            active_p = project_manager.get_active_project()
            rep = test_runner.run_project_tests(active_p["path"])
            print(f"Runner: {rep.runner} | Passed: {rep.passed} | {rep.summary}")
            if not rep.passed:
                print(rep.output)
            continue

        if prompt.startswith("/commit"):
            parts = prompt.split(maxsplit=1)
            msg = parts[1] if len(parts) > 1 else "Update via VibeCoder"
            active_p = project_manager.get_active_project()
            ok, out = git_ops.commit_all(active_p["path"], msg)
            print(out)
            continue

        if prompt.startswith("/auth"):
            from vibecoder.core.auth_manager import auth_manager
            parts = prompt.split()
            if len(parts) == 1:
                print("\n🔍 Checking AI engine authentication...")
                statuses = await auth_manager.check_all_status()
                for k, v in statuses.items():
                    print(f"  • {k.capitalize():12}: {v['status']} ({v['details']})")
            elif len(parts) >= 3:
                sub, val = parts[1].lower(), parts[2]
                if sub == "copilot":
                    ok, msg = await auth_manager.set_copilot_token(val)
                    print(("✓ " if ok else "✗ ") + msg)
                elif sub == "gemini":
                    ok, msg = await auth_manager.set_gemini_auth(val)
                    print(("✓ " if ok else "✗ ") + msg)
                elif sub in ("openrouter", "aider"):
                    ok, msg = await auth_manager.set_openrouter_key(val)
                    print(("✓ " if ok else "✗ ") + msg)
            elif len(parts) == 2 and parts[1].lower() == "login":
                print("\nInitiating Copilot OAuth device code login...")
                ok, url, code, proc = await auth_manager.start_copilot_device_login()
                if ok:
                    print(f"👉 Please open: {url}")
                    print(f"👉 Enter code:  {code}")
                    print("⏳ Waiting for authorization on GitHub...")
                    rc = await proc.wait()
                    if rc == 0:
                        print("✓ Copilot login successfully authorized!")
                    else:
                        print("✗ Copilot login expired or failed.")
                else:
                    print("✗ Could not start login:", code)
            continue

        active_p = project_manager.get_active_project()
        current_eng = engine_manager.get_engine()
        print(f"\n🧠 Running VibeCoder with [{current_eng.description}] in [{active_p['name']}]...")
        result = await engine_manager.run_vibe(prompt, project_dir=active_p["path"])

        status_str = "SUCCESS" if result.success else "FAILED"
        print(f"\n[{status_str}] Completed in {round(result.duration, 2)}s")
        if result.modified_files:
            print("Modified files:", ", ".join(result.modified_files))
        if result.diff_stat:
            print("Diff:\n", result.diff_stat)
        if result.test_report:
            print(f"Tests: {'Passed' if result.test_report.passed else 'Failed'} ({result.test_report.summary})")
        if result.error:
            print("Error:", result.error)
        elif result.output:
            print("AI Summary:\n", result.output[:500])

if __name__ == "__main__":
    asyncio.run(main())
