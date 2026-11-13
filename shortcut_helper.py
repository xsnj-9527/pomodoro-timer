"""Windows 桌面快捷方式生成工具模块。"""

import ctypes
from pathlib import Path
import subprocess
import sys

from config import APP_NAME, BASE_DIR
from icon_helper import ensure_app_icons

SHORTCUT_FILENAME = "番茄钟.lnk"


def _get_pythonw_executable() -> Path:
    """定位无控制台窗口的 pythonw.exe，不存在时回退至当前 python 解释器。"""
    exe_path = Path(sys.executable).resolve()
    pythonw = exe_path.with_name("pythonw.exe")
    if pythonw.exists():
        return pythonw
    return exe_path


def get_desktop_dir() -> Path:
    """获取当前用户的 Windows 桌面目录路径。"""
    if sys.platform.startswith("win"):
        try:
            # CSIDL_DESKTOPDIRECTORY = 0x0010
            buf = ctypes.create_unicode_buffer(260)
            res = ctypes.windll.shell32.SHGetFolderPathW(None, 0x0010, None, 0, buf)
            if res == 0 and buf.value:
                return Path(buf.value)
        except Exception:
            pass
    return Path.home() / "Desktop"


def _ps_quote(value: str) -> str:
    """对 PowerShell 单引号字符串进行转义。"""
    return "'" + value.replace("'", "''") + "'"


def create_shortcut_file(shortcut_path: Path) -> Path:
    """在指定路径创建指向本番茄钟应用的 Windows .lnk 快捷方式。"""
    target_lnk = Path(shortcut_path)
    target_lnk.parent.mkdir(parents=True, exist_ok=True)

    _, ico_path = ensure_app_icons()
    python_exe = _get_pythonw_executable()
    main_script = BASE_DIR / "main.py"

    ps_script = (
        "$ws = New-Object -ComObject WScript.Shell; "
        f"$sc = $ws.CreateShortcut({_ps_quote(str(target_lnk))}); "
        f"$sc.TargetPath = {_ps_quote(str(python_exe))}; "
        f"$sc.Arguments = {_ps_quote(chr(34) + str(main_script) + chr(34))}; "
        f"$sc.WorkingDirectory = {_ps_quote(str(BASE_DIR))}; "
        f"$sc.IconLocation = {_ps_quote(str(ico_path) + ',0')}; "
        f"$sc.Description = {_ps_quote(APP_NAME)}; "
        "$sc.Save()"
    )

    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
        capture_output=True,
        creationflags=creation_flags,
        check=False,
    )
    if completed.returncode != 0:
        raw_err = completed.stderr or completed.stdout or b""
        if isinstance(raw_err, bytes):
            err_msg = raw_err.decode("mbcs", errors="replace").strip()
        else:
            err_msg = str(raw_err).strip()
        raise OSError(err_msg or "PowerShell 创建快捷方式失败")

    if not target_lnk.exists():
        raise OSError(f"快捷方式文件未生成：{target_lnk}")

    return target_lnk


def create_desktop_shortcut() -> tuple[bool, Path, str]:
    """在项目目录及用户桌面生成应用快捷方式，返回 (桌面是否成功, 最终路径, 提示消息)。"""
    local_lnk = BASE_DIR / SHORTCUT_FILENAME
    create_shortcut_file(local_lnk)

    desktop_lnk = get_desktop_dir() / SHORTCUT_FILENAME
    try:
        create_shortcut_file(desktop_lnk)
        return True, desktop_lnk, f"已创建桌面快捷方式：{desktop_lnk}"
    except Exception as exc:
        return (
            False,
            local_lnk,
            f"已在项目目录生成快捷方式（写入桌面受限：{exc}）：{local_lnk}",
        )


if __name__ == "__main__":
    ok, path, msg = create_desktop_shortcut()
    print(msg)
    sys.exit(0 if ok else 1)
