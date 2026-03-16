from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import date
from os import environ
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"
RUNTIME_DIR = ROOT_DIR / ".runtime"
STATE_FILE = RUNTIME_DIR / "bootstrap_state.json"
BACKEND_REQUIREMENTS = BACKEND_DIR / "requirements.txt"
FRONTEND_DIST_INDEX = FRONTEND_DIR / "dist" / "index.html"
VENV_DIR = BACKEND_DIR / ".venv"
VENV_PYTHON = VENV_DIR / "Scripts" / "python.exe"
VENV_PYTHONW = VENV_DIR / "Scripts" / "pythonw.exe"
LAUNCHER_FILE = ROOT_DIR / "launcher.pyw"
PROJECT_LAUNCH_FILE = ROOT_DIR / "launch.cmd"
USER_BIN_DIR = Path.home() / ".local" / "bin"
GLOBAL_LAUNCH_SHIM = USER_BIN_DIR / "launch.cmd"
LAUNCH_SHIM_MARKER = ":: Quant Platform launch shim"


def print_step(message: str) -> None:
    print(f"[Quant] {message}")


def load_state() -> dict[str, str]:
    if not STATE_FILE.exists():
        return {}

    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_state(state: dict[str, str]) -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def hash_files(paths: list[Path]) -> str:
    digest = hashlib.sha256()

    for path in sorted(paths, key=lambda item: str(item.relative_to(ROOT_DIR)).lower()):
        digest.update(str(path.relative_to(ROOT_DIR)).encode("utf-8"))
        digest.update(path.read_bytes())

    return digest.hexdigest()


def run_command(command: list[str], cwd: Path) -> None:
    print_step(f"执行: {' '.join(command)}")
    subprocess.run(command, cwd=cwd, check=True)


def find_npm() -> str | None:
    return shutil.which("npm.cmd") or shutil.which("npm")


def _path_contains(target: Path) -> bool:
    target_value = str(target.resolve()).lower()
    for entry in environ.get("PATH", "").split(";"):
        entry = entry.strip()
        if not entry:
            continue
        try:
            if str(Path(entry).resolve()).lower() == target_value:
                return True
        except OSError:
            continue
    return False


def _build_launch_shim() -> str:
    return "\n".join(
        [
            "@echo off",
            "setlocal",
            LAUNCH_SHIM_MARKER,
            f'call "{PROJECT_LAUNCH_FILE}" %*',
            "",
        ]
    )


def ensure_global_launch_command() -> None:
    if sys.platform != "win32":
        return
    if not PROJECT_LAUNCH_FILE.exists():
        return

    USER_BIN_DIR.mkdir(parents=True, exist_ok=True)
    desired_content = _build_launch_shim()
    current_content = GLOBAL_LAUNCH_SHIM.read_text(encoding="utf-8") if GLOBAL_LAUNCH_SHIM.exists() else None
    if current_content != desired_content:
        GLOBAL_LAUNCH_SHIM.write_text(desired_content, encoding="utf-8")

    if _path_contains(USER_BIN_DIR):
        print_step(f"已安装 launch 命令: {GLOBAL_LAUNCH_SHIM}")
    else:
        print_step(f"已生成 launch 命令: {GLOBAL_LAUNCH_SHIM}")
        print_step(f"请将 {USER_BIN_DIR} 加入 PATH 后直接执行 launch")


def ensure_virtualenv() -> None:
    if VENV_PYTHON.exists():
        return

    print_step("首次运行：创建 Python 虚拟环境")
    run_command([sys.executable, "-m", "venv", str(VENV_DIR)], ROOT_DIR)


def backend_dependencies_ready() -> bool:
    probe = (
        "import importlib.util, sys; "
        "modules = ['fastapi', 'uvicorn', 'sqlalchemy', 'asyncpg', 'aiosqlite', "
        "'pydantic_settings', 'dotenv', 'typer', 'pandas', 'polars', 'tushare', "
        "'akshare', 'aiohttp', 'lightgbm', 'sklearn', 'structlog', 'PIL']; "
        "missing = [name for name in modules if importlib.util.find_spec(name) is None]; "
        "raise SystemExit(0 if not missing else 1)"
    )
    result = subprocess.run([str(VENV_PYTHON), "-c", probe], cwd=BACKEND_DIR)
    return result.returncode == 0


def ensure_backend_dependencies(state: dict[str, str]) -> None:
    requirements_hash = hash_files([BACKEND_REQUIREMENTS])
    if state.get("requirements_hash") == requirements_hash and VENV_PYTHON.exists():
        print_step("后端依赖已就绪")
        return

    if VENV_PYTHON.exists() and backend_dependencies_ready():
        print_step("检测到现有虚拟环境可直接使用")
        state["requirements_hash"] = requirements_hash
        save_state(state)
        return

    print_step("安装/更新后端依赖")
    run_command([str(VENV_PYTHON), "-m", "pip", "install", "--upgrade", "pip"], BACKEND_DIR)
    run_command([str(VENV_PYTHON), "-m", "pip", "install", "-r", "requirements.txt"], BACKEND_DIR)
    state["requirements_hash"] = requirements_hash
    save_state(state)


def dataset_ready() -> bool:
    probe = "\n".join(
        [
            "import asyncio",
            "from sqlalchemy import func, select",
            "from app.db.session import AsyncSessionLocal",
            "from app.models.daily_bar import DailyBar",
            "from app.models.screening_result import ScreeningResult",
            "",
            "async def main():",
            "    async with AsyncSessionLocal() as session:",
            "        bars = (await session.execute(",
            "            select(func.count()).select_from(DailyBar).where(DailyBar.source != 'demo_seed')",
            "        )).scalar_one()",
            "        rankings = (await session.execute(select(func.count()).select_from(ScreeningResult))).scalar_one()",
            "        raise SystemExit(0 if bars > 0 and rankings > 0 else 1)",
            "",
            "asyncio.run(main())",
        ]
    )
    result = subprocess.run([str(VENV_PYTHON), "-c", probe], cwd=BACKEND_DIR)
    return result.returncode == 0


def latest_loaded_trade_date() -> date | None:
    probe = "\n".join(
        [
            "import asyncio",
            "from sqlalchemy import func, select",
            "from app.db.session import AsyncSessionLocal",
            "from app.models.daily_bar import DailyBar",
            "",
            "async def main():",
            "    async with AsyncSessionLocal() as session:",
            "        latest = (await session.execute(",
            "            select(func.max(DailyBar.trade_date)).where(DailyBar.source != 'demo_seed')",
            "        )).scalar_one()",
            "        print(latest.isoformat() if latest else '')",
            "",
            "asyncio.run(main())",
        ]
    )
    result = subprocess.run(
        [str(VENV_PYTHON), "-c", probe],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
    )
    value = result.stdout.strip()
    return date.fromisoformat(value) if value else None


def source_latest_trade_date() -> date | None:
    probe = "\n".join(
        [
            "from app.services.market_data import build_market_data_client",
            "client = build_market_data_client('auto')",
            "latest = client.latest_open_trade_date() if hasattr(client, 'latest_open_trade_date') else None",
            "print(latest.isoformat() if latest else '')",
        ]
    )
    result = subprocess.run(
        [str(VENV_PYTHON), "-c", probe],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return date.fromisoformat(value) if value else None


def ensure_initial_market_data() -> None:
    loaded_trade_date = latest_loaded_trade_date() if dataset_ready() else None
    latest_source_trade_date = source_latest_trade_date()

    if loaded_trade_date and latest_source_trade_date is None:
        print_step(f"复用现有市场数据: {loaded_trade_date}")
        return

    if loaded_trade_date and latest_source_trade_date and loaded_trade_date >= latest_source_trade_date:
        print_step("本地市场数据已是最新")
        return

    if loaded_trade_date:
        print_step(f"检测到新交易日数据: 数据库 {loaded_trade_date} -> 数据源 {latest_source_trade_date}")
    else:
        print_step("首次初始化市场数据")

    run_command([str(VENV_PYTHON), "-m", "app.cli", "fetch-daily-bars", "--provider", "auto"], BACKEND_DIR)
    run_command([str(VENV_PYTHON), "-m", "app.cli", "compute-factors", "--provider", "auto"], BACKEND_DIR)
    run_command([str(VENV_PYTHON), "-m", "app.cli", "run-screening"], BACKEND_DIR)


def collect_frontend_inputs() -> list[Path]:
    patterns = [
        FRONTEND_DIR / "package.json",
        FRONTEND_DIR / "package-lock.json",
        FRONTEND_DIR / "index.html",
        FRONTEND_DIR / "vite.config.ts",
        FRONTEND_DIR / "tsconfig.json",
        FRONTEND_DIR / "tsconfig.node.json",
    ]
    source_files = [path for path in FRONTEND_DIR.joinpath("src").rglob("*") if path.is_file()]
    return [path for path in patterns if path.exists()] + source_files


def ensure_frontend_build(state: dict[str, str]) -> None:
    frontend_inputs = collect_frontend_inputs()
    frontend_hash = hash_files(frontend_inputs)

    if FRONTEND_DIST_INDEX.exists() and state.get("frontend_hash") == frontend_hash:
        print_step("前端静态资源已就绪")
        return

    npm = find_npm()
    if not npm:
        if FRONTEND_DIST_INDEX.exists():
            print_step("未检测到 Node.js，继续使用现有前端构建产物")
            return
        raise RuntimeError("未检测到 Node.js / npm，无法首次构建前端页面。")

    if not FRONTEND_DIR.joinpath("node_modules").exists():
        print_step("首次运行：安装前端依赖")
        run_command([npm, "install"], FRONTEND_DIR)

    print_step("构建前端静态页面")
    run_command([npm, "run", "build"], FRONTEND_DIR)
    state["frontend_hash"] = frontend_hash
    save_state(state)


def ensure_icons_and_shortcuts() -> None:
    if not VENV_PYTHON.exists():
        return

    print_step("Refreshing icons and desktop shortcuts")
    result = subprocess.run(
        [
            str(VENV_PYTHON),
            "-m",
            "app.utils.icon_generator",
            "--sync-shortcuts",
            "--project-root",
            str(ROOT_DIR),
        ],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print_step("Icon refresh failed, continuing app launch")
        if result.stderr.strip():
            print_step(result.stderr.strip())


def launch_app() -> None:
    pythonw = VENV_PYTHONW if VENV_PYTHONW.exists() else VENV_PYTHON
    if not pythonw.exists():
        raise RuntimeError("未找到可用的 Python 启动器。")

    print_step("启动量化平台")
    subprocess.Popen([str(pythonw), str(LAUNCHER_FILE)], cwd=ROOT_DIR)


def main() -> int:
    try:
        print_step("检查本地启动环境")
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        ensure_global_launch_command()
        state = load_state()
        ensure_virtualenv()
        ensure_backend_dependencies(state)
        ensure_initial_market_data()
        ensure_frontend_build(state)
        ensure_icons_and_shortcuts()
        launch_app()
        print_step("已切到后台启动，桌面 UI 会自动打开")
        return 0
    except subprocess.CalledProcessError as exc:
        print_step(f"命令执行失败，退出码: {exc.returncode}")
        return exc.returncode or 1
    except Exception as exc:
        print_step(f"启动失败：{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
