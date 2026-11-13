"""番茄钟桌面应用入口文件。"""

from icon_helper import set_windows_app_id
from ui.app import PomodoroApp


def main() -> None:
    """启动番茄钟应用主循环。"""
    set_windows_app_id()
    app = PomodoroApp()
    app.mainloop()


if __name__ == "__main__":
    main()
