"""系统托盘图标与右键快捷菜单管理模块。"""

from collections.abc import Callable
import threading

import pystray

from config import APP_NAME
from icon_helper import get_tray_image


class TrayManager:
    """封装 pystray 系统托盘图标及线程安全的 Tkinter 回调调度。"""

    def __init__(
        self,
        app,
        on_show_main: Callable[[], None],
        on_toggle_mini: Callable[[], None],
        on_start_pause: Callable[[], None],
        on_reset: Callable[[], None],
        on_quit: Callable[[], None],
    ) -> None:
        self._app = app
        self._on_show_main = on_show_main
        self._on_toggle_mini = on_toggle_mini
        self._on_start_pause = on_start_pause
        self._on_reset = on_reset
        self._on_quit = on_quit

        self._icon: pystray.Icon | None = None
        self._thread: threading.Thread | None = None
        self._running = False

    @property
    def is_running(self) -> bool:
        """返回托盘图标是否处于运行状态。"""
        return self._running

    def _schedule(self, callback: Callable[[], None]) -> None:
        """将托盘线程中的点击事件安全调度到 Tkinter 主线程执行。"""
        try:
            self._app.after(0, callback)
        except Exception:
            pass

    def start(self) -> bool:
        """在后台守护线程中启动系统托盘图标。"""
        if self._running:
            return True
        try:
            image = get_tray_image()
            menu = pystray.Menu(
                pystray.MenuItem(
                    "显示主窗口",
                    lambda _icon, _item: self._schedule(self._on_show_main),
                    default=True,
                ),
                pystray.MenuItem(
                    "切换迷你悬浮窗",
                    lambda _icon, _item: self._schedule(self._on_toggle_mini),
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    "开始 / 暂停",
                    lambda _icon, _item: self._schedule(self._on_start_pause),
                ),
                pystray.MenuItem(
                    "重置计时",
                    lambda _icon, _item: self._schedule(self._on_reset),
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    "退出应用",
                    lambda _icon, _item: self._schedule(self._on_quit),
                ),
            )
            self._icon = pystray.Icon("pomodoro_timer", image, APP_NAME, menu)
            self._running = True
            self._thread = threading.Thread(target=self._run_icon, daemon=True)
            self._thread.start()
            return True
        except Exception:
            self._running = False
            self._icon = None
            return False

    def _run_icon(self) -> None:
        """运行托盘事件循环。"""
        if self._icon is None:
            return
        try:
            self._icon.run()
        except Exception:
            pass
        finally:
            self._running = False

    def update_tooltip(self, text: str) -> None:
        """更新系统托盘悬停提示文本。"""
        if self._icon is not None and self._running:
            try:
                self._icon.title = text
            except Exception:
                pass

    def stop(self) -> None:
        """停止并移除系统托盘图标。"""
        self._running = False
        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception:
                pass
            self._icon = None
