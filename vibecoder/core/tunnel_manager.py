"""
Cloudflare Tunnel & Localhost Port Hosting Manager for VibeCoder.
Enables instant public HTTPS access to local development servers and APIs.
"""

import asyncio
import json
import logging
import os
import re
import shutil
import signal
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from vibecoder.config import WORKSPACE_ROOT, CODESPACE_NAME, settings

logger = logging.getLogger("TunnelManager")

TUNNELS_FILE = WORKSPACE_ROOT / "storage" / "vibecoder" / "tunnels.json"
CLOUDFLARED_BIN = shutil.which("cloudflared") or "/usr/local/bin/cloudflared"

class TunnelManager:
    """Manages Cloudflare quick tunnels and background web servers."""

    def __init__(self):
        self._active_tunnels: Dict[int, Dict[str, Any]] = {}
        self._active_servers: Dict[str, Dict[str, Any]] = {}
        self._load_state()

    def _load_state(self):
        """Load persisted tunnel metadata and prune dead processes."""
        if TUNNELS_FILE.exists():
            try:
                data = json.loads(TUNNELS_FILE.read_text(encoding="utf-8"))
                for port_str, info in data.get("tunnels", {}).items():
                    port = int(port_str)
                    pid = info.get("pid")
                    # Check if pid is still running and is cloudflared
                    if pid and self._is_pid_running(pid, "cloudflared"):
                        self._active_tunnels[port] = info
                self._save_state()
            except Exception as e:
                logger.warning(f"Error loading tunnel state: {e}")

    def _save_state(self):
        """Persist active tunnels to disk."""
        TUNNELS_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            payload = {
                "updated_at": time.time(),
                "tunnels": {str(k): v for k, v in self._active_tunnels.items()}
            }
            TUNNELS_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Error saving tunnel state: {e}")

    @staticmethod
    def _is_pid_running(pid: int, expected_name: Optional[str] = None) -> bool:
        """Check if process PID is running."""
        try:
            os.kill(pid, 0)
            if expected_name:
                comm_file = Path(f"/proc/{pid}/comm")
                if comm_file.exists():
                    comm = comm_file.read_text().strip().lower()
                    return expected_name.lower() in comm
            return True
        except (ProcessLookupError, PermissionError):
            return False

    def get_active_ports(self) -> List[Dict[str, Any]]:
        """Scan and detect all listening TCP ports on localhost."""
        ports = []
        try:
            proc = subprocess.run(["ss", "-tlpn"], capture_output=True, text=True, timeout=5)
            for line in proc.stdout.splitlines()[1:]:
                parts = line.split()
                if len(parts) >= 4:
                    local_addr = parts[3]
                    port_str = local_addr.rsplit(":", 1)[-1]
                    try:
                        p = int(port_str)
                        # Skip system dns/rpc internal ports
                        if p in (53, 2222, 25958):
                            continue
                        prog = parts[5] if len(parts) >= 6 else ""
                        m = re.search(r'\"([^\"]+)\",pid=(\d+)', prog)
                        pname = m.group(1) if m else "service"
                        pid = int(m.group(2)) if m else None

                        ports.append({
                            "port": p,
                            "process": pname,
                            "pid": pid,
                            "addr": local_addr,
                            "is_tunneled": (p in self._active_tunnels),
                            "tunnel_url": self._active_tunnels.get(p, {}).get("url")
                        })
                    except ValueError:
                        pass
        except Exception as e:
            logger.warning(f"Failed to scan ports via ss: {e}")

        # Deduplicate by port
        seen = set()
        unique = []
        for item in sorted(ports, key=lambda x: x["port"]):
            if item["port"] not in seen:
                seen.add(item["port"])
                unique.append(item)
        return unique

    async def start_tunnel(self, port: int, service_name: Optional[str] = None) -> Tuple[bool, str, Optional[str]]:
        """Start a Cloudflare Quick Tunnel exposing http://localhost:<port>."""
        if not os.path.exists(CLOUDFLARED_BIN):
            return False, f"Cloudflare binary not found at {CLOUDFLARED_BIN}", None

        # If tunnel already active for this port, return existing
        if port in self._active_tunnels:
            info = self._active_tunnels[port]
            if self._is_pid_running(info.get("pid", 0), "cloudflared"):
                return True, f"Tunnel already running on port {port}", info.get("url")
            else:
                self._active_tunnels.pop(port, None)

        cmd = [CLOUDFLARED_BIN, "tunnel", "--url", f"http://localhost:{port}"]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Wait for public URL in stderr stream
            url = None
            timeout_seconds = 18
            start_wait = time.time()
            extracted_lines = []

            while time.time() - start_wait < timeout_seconds:
                if proc.returncode is not None:
                    break
                try:
                    line = await asyncio.wait_for(proc.stderr.readline(), timeout=2.0)
                    if not line:
                        break
                    line_str = line.decode("utf-8", errors="replace").strip()
                    extracted_lines.append(line_str)
                    match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line_str)
                    if match:
                        url = match.group(0)
                        break
                except asyncio.TimeoutError:
                    continue

            if not url:
                try:
                    proc.terminate()
                except Exception:
                    pass
                err_summary = "\n".join(extracted_lines[-4:]) if extracted_lines else "Tunnel initialization timed out."
                return False, f"Could not acquire Cloudflare URL:\n{err_summary}", None

            tunnel_info = {
                "port": port,
                "url": url,
                "pid": proc.pid,
                "service": service_name or f"Port {port}",
                "started_at": time.time(),
                "codespace_dev_url": f"https://{CODESPACE_NAME}-{port}.app.github.dev" if CODESPACE_NAME else None
            }
            self._active_tunnels[port] = tunnel_info
            self._save_state()

            logger.info(f"Cloudflare tunnel established: port {port} -> {url} (PID {proc.pid})")
            return True, f"Tunnel active for port {port}!", url

        except Exception as e:
            logger.error(f"Failed to launch cloudflared for port {port}: {e}", exc_info=True)
            return False, f"Tunnel creation failed: {str(e)}", None

    def stop_tunnel(self, port: int) -> Tuple[bool, str]:
        """Stop an active tunnel on specified port."""
        if port not in self._active_tunnels:
            return False, f"No active tunnel found for port {port}"

        info = self._active_tunnels.pop(port)
        pid = info.get("pid")
        if pid and self._is_pid_running(pid):
            try:
                os.kill(pid, signal.SIGTERM)
                time.sleep(0.3)
                if self._is_pid_running(pid):
                    os.kill(pid, signal.SIGKILL)
            except Exception as e:
                logger.warning(f"Error terminating tunnel PID {pid}: {e}")

        self._save_state()
        return True, f"Tunnel for port {port} stopped."

    def list_tunnels(self) -> List[Dict[str, Any]]:
        """Return list of all live active tunnels."""
        active = []
        for port, info in list(self._active_tunnels.items()):
            if self._is_pid_running(info.get("pid", 0), "cloudflared"):
                info_copy = dict(info)
                info_copy["uptime"] = int(time.time() - info.get("started_at", time.time()))
                active.append(info_copy)
            else:
                self._active_tunnels.pop(port, None)
        self._save_state()
        return active

    async def auto_serve_project(self, project_path: str, custom_port: Optional[int] = None) -> Tuple[bool, str, Optional[int]]:
        """Detect and launch web server for project in background, then return port."""
        p = Path(project_path).resolve()
        proj_name = p.name

        # Check if server already running for this project
        if proj_name in self._active_servers:
            srv = self._active_servers[proj_name]
            if self._is_pid_running(srv.get("pid", 0)):
                return True, f"Server already running for {proj_name} on port {srv['port']}", srv['port']
            else:
                self._active_servers.pop(proj_name, None)

        port = custom_port or 8000
        # If port is occupied, find next available port
        active_ports = {item["port"] for item in self.get_active_ports()}
        while port in active_ports:
            port += 1

        cmd = None
        server_type = "Generic Server"

        # 1. FastAPI / Uvicorn
        if (p / "main.py").exists():
            main_content = (p / "main.py").read_text(encoding="utf-8", errors="ignore")
            if "FastAPI" in main_content or "app = FastAPI" in main_content:
                cmd = ["python3", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", str(port)]
                server_type = "FastAPI (Uvicorn)"
            elif "Flask" in main_content:
                cmd = ["python3", "main.py"]
                server_type = "Flask App"
            else:
                cmd = ["python3", "main.py"]
                server_type = "Python App"
        elif (p / "app.py").exists():
            app_content = (p / "app.py").read_text(encoding="utf-8", errors="ignore")
            if "FastAPI" in app_content:
                cmd = ["python3", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", str(port)]
                server_type = "FastAPI (Uvicorn)"
            elif "streamlit" in app_content:
                cmd = ["python3", "-m", "streamlit", "run", "app.py", "--server.port", str(port), "--server.headless", "true"]
                server_type = "Streamlit App"
            else:
                cmd = ["python3", "app.py"]
                server_type = "Python App"
        elif (p / "package.json").exists():
            pkg = (p / "package.json").read_text(encoding="utf-8", errors="ignore")
            if '"start"' in pkg:
                cmd = ["npm", "start"]
                server_type = "Node.js (npm start)"
            elif '"dev"' in pkg:
                cmd = ["npm", "run", "dev", "--", "--port", str(port), "--host"]
                server_type = "Vite/Node (npm run dev)"
        elif any(p.glob("*.html")):
            cmd = ["python3", "-m", "http.server", str(port)]
            server_type = "Static Web Server (HTML/JS)"

        if not cmd:
            # Fallback default static server
            cmd = ["python3", "-m", "http.server", str(port)]
            server_type = "Directory HTTP Server"

        try:
            env = os.environ.copy()
            env["PORT"] = str(port)
            proc = subprocess.Popen(
                cmd,
                cwd=str(p),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=env,
                preexec_fn=os.setsid
            )

            # Wait briefly to ensure server doesn't immediately crash
            await asyncio.sleep(1.2)
            if proc.poll() is not None:
                return False, f"Server process exited prematurely with code {proc.returncode}", None

            self._active_servers[proj_name] = {
                "project": proj_name,
                "port": port,
                "pid": proc.pid,
                "server_type": server_type,
                "started_at": time.time()
            }

            logger.info(f"Launched {server_type} for {proj_name} on port {port} (PID {proc.pid})")
            return True, f"Launched {server_type} on port {port}!", port

        except Exception as e:
            logger.error(f"Failed to run server for {proj_name}: {e}", exc_info=True)
            return False, f"Server launch failed: {str(e)}", None

    def stop_server(self, project_name: str) -> Tuple[bool, str]:
        """Stop background server running for project."""
        if project_name not in self._active_servers:
            return False, f"No server running for project '{project_name}'"

        srv = self._active_servers.pop(project_name)
        pid = srv.get("pid")
        if pid and self._is_pid_running(pid):
            try:
                os.killpg(os.getpgid(pid), signal.SIGTERM)
                time.sleep(0.3)
                if self._is_pid_running(pid):
                    os.killpg(os.getpgid(pid), signal.SIGKILL)
            except Exception as e:
                logger.warning(f"Error terminating server group PID {pid}: {e}")

        return True, f"Server for '{project_name}' stopped."

    def stop_all(self):
        """Cleanup all active tunnels and servers."""
        for port in list(self._active_tunnels.keys()):
            self.stop_tunnel(port)
        for proj in list(self._active_servers.keys()):
            self.stop_server(proj)

tunnel_manager = TunnelManager()
