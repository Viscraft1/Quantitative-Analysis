from __future__ import annotations

import ctypes
import shutil
import subprocess
import time
import webbrowser
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
RUNTIME_DIR = ROOT_DIR / ".runtime"
PID_FILE = RUNTIME_DIR / "backend.pid"
LOG_FILE = RUNTIME_DIR / "backend.log"
VENV_PYTHON = BACKEND_DIR / ".venv" / "Scripts" / "python.exe"
APP_URL = "http://127.0.0.1:8000"
HEALTH_URL = f"{APP_URL}/api/v1/health"
STARTUP_TIMEOUT_SECONDS = 25
WINDOW_TITLE = "量化分析平台"

BROWSER_CANDIDATES = [
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
]


def show_message(message: str, title: str = WINDOW_TITLE, icon: int = 0x40) -> None:
    try:
        ctypes.windll.user32.MessageBoxW(0, message, title, icon)
    except Exception:
        pass


def service_ready() -> bool:
    try:
        with urlopen(HEALTH_URL, timeout=1.5) as response:
            return response.status == 200
    except URLError:
        return False
    except Exception:
        return False


def wait_until_ready(timeout_seconds: int) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if service_ready():
            return True
        time.sleep(0.5)
    return False


def cleanup_stale_backend() -> None:
    if not PID_FILE.exists():
        return

    try:
        stale_pid = PID_FILE.read_text(encoding="utf-8").strip()
    except Exception:
        PID_FILE.unlink(missing_ok=True)
        return

    if not stale_pid:
        PID_FILE.unlink(missing_ok=True)
        return

    try:
        subprocess.run(
            ["taskkill", "/PID", stale_pid, "/T", "/F"],
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception:
        pass
    finally:
        PID_FILE.unlink(missing_ok=True)


def start_backend() -> subprocess.Popen[bytes]:
    if not VENV_PYTHON.exists():
        raise RuntimeError("未找到 backend/.venv，请先运行 start.bat 完成初始化。")

    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    log_handle = LOG_FILE.open("ab")
    process = subprocess.Popen(
        [
            str(VENV_PYTHON),
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        cwd=BACKEND_DIR,
        stdout=log_handle,
        stderr=log_handle,
        creationflags=creation_flags,
    )
    PID_FILE.write_text(str(process.pid), encoding="utf-8")
    return process


def find_app_browser() -> Path | None:
    for command_name in ("msedge.exe", "chrome.exe"):
        resolved = shutil.which(command_name)
        if resolved:
            return Path(resolved)

    for candidate in BROWSER_CANDIDATES:
        if candidate.exists():
            return candidate

    return None


def open_desktop_ui() -> None:
    browser_path = find_app_browser()
    if browser_path is not None:
        subprocess.Popen(
            [
                str(browser_path),
                f"--app={APP_URL}",
                "--new-window",
                "--window-size=1440,920",
            ],
            creationflags=getattr(subprocess, "DETACHED_PROCESS", 0),
        )
        return

    webbrowser.open(APP_URL)


def main() -> None:
    try:
        if not service_ready():
            if PID_FILE.exists() and wait_until_ready(4):
                pass
            else:
                cleanup_stale_backend()
                started_process = start_backend()
                if not wait_until_ready(STARTUP_TIMEOUT_SECONDS):
                    if started_process.poll() is not None:
                        PID_FILE.unlink(missing_ok=True)
                    raise RuntimeError(
                        "量化平台启动失败，请双击 start.bat 查看初始化日志，或检查 .runtime/backend.log。"
                    )

        open_desktop_ui()
    except Exception as exc:
        show_message(str(exc), icon=0x10)


if __name__ == "__main__":
    main()
