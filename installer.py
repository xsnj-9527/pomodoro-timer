"""独立 .exe 安装向导程序（支持 GUI 向导与 --silent 静默安装）。"""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tkinter import filedialog

import customtkinter as ctk

from config import COLORS, FONT_FAMILY, ICON_ICO_PATH, RESOURCE_DIR
from icon_helper import apply_window_icon, set_windows_app_id
from shortcut_helper import SHORTCUT_FILENAME, create_exe_shortcut, get_desktop_dir

INSTALLER_APP_NAME = "番茄钟 v1.0.0 安装向导"
EXE_FILENAME = "番茄钟.exe"


def get_default_install_dir() -> Path:
    """获取默认用户级安装目录（无需管理员权限）。"""
    local_app_data = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(local_app_data) / "Programs" / "PomodoroTimer"


def get_start_menu_programs_dir() -> Path:
    """获取当前用户的开始菜单程序目录。"""
    app_data = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(app_data) / "Microsoft" / "Windows" / "Start Menu" / "Programs"


def resolve_payload_exe() -> Path:
    """定位内嵌或本地构建的主程序番茄钟.exe。"""
    bundled = RESOURCE_DIR / "payload" / EXE_FILENAME
    if bundled.exists():
        return bundled
    local_dist = Path(__file__).resolve().parent / "dist" / EXE_FILENAME
    if local_dist.exists():
        return local_dist
    raise FileNotFoundError(f"未找到安装包内嵌程序：{bundled}")


def _write_uninstall_script(
    install_dir: Path,
    desktop_lnk: Path | None,
    start_menu_lnk: Path | None,
) -> Path:
    """在安装目录生成一键卸载脚本。"""
    uninstall_bat = install_dir / "卸载番茄钟.bat"
    lines = [
        "@echo off",
        "chcp 65001 >nul",
        "echo 正在停止番茄钟进程...",
        f'taskkill /F /IM "{EXE_FILENAME}" >nul 2>&1',
    ]
    if desktop_lnk is not None:
        lines.append(f'if exist "{desktop_lnk}" del /F /Q "{desktop_lnk}"')
    if start_menu_lnk is not None:
        lines.append(f'if exist "{start_menu_lnk}" del /F /Q "{start_menu_lnk}"')
    lines.extend(
        [
            "echo 正在清理安装目录...",
            f'start "" /b cmd /c timeout /t 2 /nobreak ^>nul ^& rmdir /s /q "{install_dir}"',
            "echo 番茄钟已卸载完成。",
        ]
    )
    uninstall_bat.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
    return uninstall_bat


def perform_install(
    install_dir: Path,
    create_desktop: bool = True,
    create_start_menu: bool = True,
    payload_exe: Path | None = None,
) -> dict:
    """执行独立程序复制、快捷方式与卸载脚本创建。"""
    target_dir = Path(install_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    source_exe = Path(payload_exe) if payload_exe else resolve_payload_exe()
    if not source_exe.exists():
        raise FileNotFoundError(f"找不到待安装的可执行文件：{source_exe}")

    installed_exe = target_dir / EXE_FILENAME
    shutil.copy2(source_exe, installed_exe)

    installed_ico = target_dir / "pomodoro.ico"
    if ICON_ICO_PATH.exists():
        shutil.copy2(ICON_ICO_PATH, installed_ico)

    desktop_lnk: Path | None = None
    if create_desktop:
        desktop_lnk = get_desktop_dir() / SHORTCUT_FILENAME
        create_exe_shortcut(
            exe_path=installed_exe,
            shortcut_path=desktop_lnk,
            icon_path=installed_ico if installed_ico.exists() else installed_exe,
        )

    start_menu_lnk: Path | None = None
    if create_start_menu:
        start_menu_lnk = get_start_menu_programs_dir() / SHORTCUT_FILENAME
        create_exe_shortcut(
            exe_path=installed_exe,
            shortcut_path=start_menu_lnk,
            icon_path=installed_ico if installed_ico.exists() else installed_exe,
        )

    uninstall_bat = _write_uninstall_script(target_dir, desktop_lnk, start_menu_lnk)

    return {
        "install_dir": target_dir,
        "installed_exe": installed_exe,
        "desktop_shortcut": desktop_lnk,
        "start_menu_shortcut": start_menu_lnk,
        "uninstall_script": uninstall_bat,
    }


def launch_installed_app(installed_exe: Path) -> None:
    """安装完成后以独立进程启动已安装的番茄钟.exe。"""
    creation_flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(
        subprocess, "CREATE_NEW_PROCESS_GROUP", 0
    )
    subprocess.Popen(
        [str(installed_exe)],
        cwd=str(installed_exe.parent),
        creationflags=creation_flags,
    )


class PomodoroInstallerApp(ctk.CTk):
    """番茄钟独立安装包图形化安装向导。"""

    def __init__(self) -> None:
        set_windows_app_id("antigravity.pomodoro.timer.installer.1")
        super().__init__()
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self._installed_exe: Path | None = None
        self._configure_window()
        self._build_ui()

    def _configure_window(self) -> None:
        self.title(INSTALLER_APP_NAME)
        self.configure(fg_color=COLORS["bg"])
        self.resizable(False, False)

        width, height = 460, 380
        self.update_idletasks()
        pos_x = max(0, (self.winfo_screenwidth() - width) // 2)
        pos_y = max(0, (self.winfo_screenheight() - height) // 2)
        self.geometry(f"{width}x{height}+{pos_x}+{pos_y}")

        apply_window_icon(self)
        self.after(200, lambda: apply_window_icon(self))

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=24, pady=(20, 12), sticky="ew")

        ctk.CTkLabel(
            header,
            text="🍅 番茄钟 v1.0.0 安装向导",
            font=(FONT_FAMILY, 20, "bold"),
            text_color=COLORS["text_primary"],
        ).pack(anchor="w")

        ctk.CTkLabel(
            header,
            text="独立桌面版 · 无需安装 Python 环境即可直接运行",
            font=(FONT_FAMILY, 12),
            text_color=COLORS["text_secondary"],
        ).pack(anchor="w", pady=(4, 0))

        card = ctk.CTkFrame(
            self,
            fg_color=COLORS["card"],
            border_width=1,
            border_color=COLORS["card_border"],
            corner_radius=12,
        )
        card.grid(row=1, column=0, padx=24, pady=(0, 14), sticky="ew")
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card,
            text="安装位置",
            font=(FONT_FAMILY, 12, "bold"),
            text_color=COLORS["text_primary"],
        ).grid(row=0, column=0, padx=16, pady=(14, 4), sticky="w")

        path_row = ctk.CTkFrame(card, fg_color="transparent")
        path_row.grid(row=1, column=0, padx=16, pady=(0, 12), sticky="ew")
        path_row.grid_columnconfigure(0, weight=1)

        self.dir_entry = ctk.CTkEntry(
            path_row,
            height=34,
            font=(FONT_FAMILY, 12),
            fg_color=COLORS["subtle_bg"],
            border_color=COLORS["card_border"],
        )
        self.dir_entry.insert(0, str(get_default_install_dir()))
        self.dir_entry.grid(row=0, column=0, padx=(0, 8), sticky="ew")

        self.browse_btn = ctk.CTkButton(
            path_row,
            text="浏览...",
            width=72,
            height=34,
            corner_radius=8,
            font=(FONT_FAMILY, 12),
            fg_color=COLORS["neutral_btn"],
            hover_color=COLORS["neutral_btn_hover"],
            text_color=COLORS["neutral_btn_text"],
            command=self._choose_dir,
        )
        self.browse_btn.grid(row=0, column=1)

        self.desktop_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            card,
            text="创建桌面快捷方式",
            variable=self.desktop_var,
            font=(FONT_FAMILY, 12),
            fg_color=COLORS["focus_primary"],
            hover_color=COLORS["focus_hover"],
        ).grid(row=2, column=0, padx=16, pady=4, sticky="w")

        self.start_menu_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            card,
            text="创建开始菜单快捷方式",
            variable=self.start_menu_var,
            font=(FONT_FAMILY, 12),
            fg_color=COLORS["focus_primary"],
            hover_color=COLORS["focus_hover"],
        ).grid(row=3, column=0, padx=16, pady=4, sticky="w")

        self.launch_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            card,
            text="安装完成后立即启动番茄钟",
            variable=self.launch_var,
            font=(FONT_FAMILY, 12),
            fg_color=COLORS["focus_primary"],
            hover_color=COLORS["focus_hover"],
        ).grid(row=4, column=0, padx=16, pady=(4, 14), sticky="w")

        self.progress_bar = ctk.CTkProgressBar(
            self,
            height=8,
            corner_radius=4,
            progress_color=COLORS["focus_primary"],
            fg_color=COLORS["subtle_bg"],
        )
        self.progress_bar.grid(row=2, column=0, padx=24, pady=(0, 8), sticky="ew")
        self.progress_bar.set(0.0)

        self.status_label = ctk.CTkLabel(
            self,
            text="点击「立即安装」开始部署应用",
            font=(FONT_FAMILY, 12),
            text_color=COLORS["text_secondary"],
        )
        self.status_label.grid(row=3, column=0, padx=24, pady=(0, 12), sticky="w")

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.grid(row=4, column=0, padx=24, pady=(0, 20), sticky="ew")
        btn_row.grid_columnconfigure(0, weight=1)

        self.install_btn = ctk.CTkButton(
            btn_row,
            text="立即安装",
            height=40,
            corner_radius=10,
            font=(FONT_FAMILY, 14, "bold"),
            fg_color=COLORS["focus_primary"],
            hover_color=COLORS["focus_hover"],
            command=self._handle_install,
        )
        self.install_btn.grid(row=0, column=0, sticky="ew")

    def _choose_dir(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.dir_entry.get().strip() or None)
        if selected:
            self.dir_entry.delete(0, "end")
            self.dir_entry.insert(0, str(Path(selected) / "PomodoroTimer"))

    def _handle_install(self) -> None:
        if self._installed_exe is not None:
            if self.launch_var.get() and self._installed_exe.exists():
                launch_installed_app(self._installed_exe)
            self.destroy()
            return

        install_path_str = self.dir_entry.get().strip()
        if not install_path_str:
            self.status_label.configure(text="请先选择有效的安装路径", text_color=COLORS["error_text"])
            return

        self.install_btn.configure(state="disabled", text="正在安装...")
        self.progress_bar.set(0.45)
        self.update_idletasks()

        try:
            result = perform_install(
                install_dir=Path(install_path_str),
                create_desktop=self.desktop_var.get(),
                create_start_menu=self.start_menu_var.get(),
            )
            self._installed_exe = result["installed_exe"]
            self.progress_bar.set(1.0)
            self.progress_bar.configure(progress_color=COLORS["success_text"])
            self.status_label.configure(
                text=f"安装成功！位置：{result['install_dir']}",
                text_color=COLORS["success_text"],
            )
            self.install_btn.configure(
                state="normal",
                text="完成",
                fg_color=COLORS["break_primary"],
                hover_color=COLORS["break_hover"],
            )
        except Exception as exc:
            self.progress_bar.set(0.0)
            self.status_label.configure(
                text=f"安装失败：{exc}",
                text_color=COLORS["error_text"],
            )
            self.install_btn.configure(state="normal", text="重试安装")


def main() -> int:
    parser = argparse.ArgumentParser(description=INSTALLER_APP_NAME)
    parser.add_argument("--silent", action="store_true", help="无界面静默安装")
    parser.add_argument("--dir", type=str, default="", help="指定静默安装目录")
    args = parser.parse_args()

    if args.silent:
        target_dir = Path(args.dir) if args.dir else get_default_install_dir()
        result = perform_install(
            install_dir=target_dir,
            create_desktop=True,
            create_start_menu=True,
        )
        print(f"安装完成：{result['installed_exe']}")
        return 0

    app = PomodoroInstallerApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
