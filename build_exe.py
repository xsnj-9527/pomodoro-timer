"""自动化打包脚本：构建独立绿色版 番茄钟.exe 与独立安装包 番茄钟_Setup_v1.0.0.exe。"""

from pathlib import Path
import sys

import PyInstaller.__main__

from config import BASE_DIR
from icon_helper import ensure_app_icons


def build_all() -> tuple[Path, Path]:
    """执行两阶段 PyInstaller 打包并返回生成的两个 .exe 路径。"""
    project_root = Path(BASE_DIR).resolve()
    assets_dir = project_root / "assets"
    dist_dir = project_root / "dist"
    ico_path = assets_dir / "pomodoro.ico"
    png_path = assets_dir / "pomodoro.png"

    ensure_app_icons(png_path=png_path, ico_path=ico_path)

    # 第一阶段：打包独立单文件主程序 dist/番茄钟.exe
    print("[1/2] 正在构建独立单文件主程序 dist/番茄钟.exe ...")
    PyInstaller.__main__.run(
        [
            str(project_root / "main.py"),
            "--name=番茄钟",
            "--onefile",
            "--windowed",
            "--noconfirm",
            "--clean",
            f"--icon={ico_path}",
            f"--add-data={assets_dir};assets",
            "--collect-all=customtkinter",
            "--collect-all=pystray",
            f"--distpath={dist_dir}",
            f"--workpath={project_root / 'build' / 'app'}",
            f"--specpath={project_root / 'build'}",
        ]
    )

    app_exe = dist_dir / "番茄钟.exe"
    if not app_exe.exists():
        raise FileNotFoundError(f"主程序打包失败，未找到：{app_exe}")

    # 第二阶段：将主程序打入安装向导，生成 dist/番茄钟_Setup_v1.0.0.exe
    print("[2/2] 正在构建独立安装包 dist/番茄钟_Setup_v1.0.0.exe ...")
    PyInstaller.__main__.run(
        [
            str(project_root / "installer.py"),
            "--name=番茄钟_Setup_v1.0.0",
            "--onefile",
            "--windowed",
            "--noconfirm",
            "--clean",
            f"--icon={ico_path}",
            f"--add-data={assets_dir};assets",
            f"--add-data={app_exe};payload",
            "--collect-all=customtkinter",
            f"--distpath={dist_dir}",
            f"--workpath={project_root / 'build' / 'installer'}",
            f"--specpath={project_root / 'build'}",
        ]
    )

    setup_exe = dist_dir / "番茄钟_Setup_v1.0.0.exe"
    if not setup_exe.exists():
        raise FileNotFoundError(f"安装包打包失败，未找到：{setup_exe}")

    print(f"构建成功：\n  - 绿色独立版：{app_exe}\n  - 独立安装包：{setup_exe}")
    return app_exe, setup_exe


if __name__ == "__main__":
    try:
        build_all()
    except Exception as exc:
        print(f"打包失败：{exc}", file=sys.stderr)
        sys.exit(1)
