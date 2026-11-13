"""声音提醒与系统通知模块（在后台线程异步执行，不阻塞 UI）。"""

import subprocess
import sys
import threading
import time


class Notifier:
    """跨平台桌面提示音与 Windows 系统通知发送器。"""

    def notify(self, title: str, message: str, sound: bool = True) -> None:
        """异步触发声音与系统通知。"""
        thread = threading.Thread(
            target=self._dispatch,
            args=(title, message, sound),
            daemon=True,
        )
        thread.start()

    def _dispatch(self, title: str, message: str, sound: bool) -> None:
        """在后台线程中依次触发声音提醒与系统通知。"""
        if sound:
            self._play_sound()
        self._send_system_notification(title, message)

    @staticmethod
    def _play_sound() -> None:
        """播放柔和的完成提示音。"""
        if sys.platform.startswith("win"):
            try:
                import winsound

                # 播放轻快的三连音（A5 -> C6 -> E6）
                for freq, duration in ((880, 140), (1046, 140), (1318, 220)):
                    winsound.Beep(freq, duration)
                    time.sleep(0.03)
                return
            except Exception:
                try:
                    import winsound

                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                    return
                except Exception:
                    pass
        # 非 Windows 或音频接口不可用时使用标准终端响铃
        try:
            print("\a", end="", flush=True)
        except Exception:
            pass

    @staticmethod
    def _send_system_notification(title: str, message: str) -> None:
        """发送系统桌面通知（Windows 下使用 PowerShell NotifyIcon 气泡）。"""
        if not sys.platform.startswith("win"):
            return

        # 对单引号做 PowerShell 字符串转义，避免脚本语法错误
        safe_title = title.replace("'", "''")
        safe_message = message.replace("'", "''")

        ps_script = (
            "Add-Type -AssemblyName System.Windows.Forms; "
            "Add-Type -AssemblyName System.Drawing; "
            "$notify = New-Object System.Windows.Forms.NotifyIcon; "
            "$notify.Icon = [System.Drawing.SystemIcons]::Information; "
            "$notify.Visible = $true; "
            f"$notify.ShowBalloonTip(5000, '{safe_title}', '{safe_message}', "
            "[System.Windows.Forms.ToolTipIcon]::Info); "
            "Start-Sleep -Seconds 6; "
            "$notify.Dispose()"
        )

        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            subprocess.Popen(
                ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creation_flags,
            )
        except Exception:
            # 系统通知失败不应影响主程序运行
            pass
