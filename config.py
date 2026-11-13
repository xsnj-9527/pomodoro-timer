"""全局配置与主题常量模块。"""

import os
from pathlib import Path
import sys


def _is_dir_writable(directory: Path) -> bool:
    """检测目标目录是否可写，避免打包后写入受保护目录失败。"""
    try:
        directory.mkdir(parents=True, exist_ok=True)
        probe = directory / ".write_probe.tmp"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


# 区分 PyInstaller 冻结环境与源码环境的资源/数据目录
if getattr(sys, "frozen", False):
    RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    _exe_dir = Path(sys.executable).resolve().parent
    if _is_dir_writable(_exe_dir):
        APP_HOME_DIR = _exe_dir
    else:
        APP_HOME_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "PomodoroTimer"
else:
    RESOURCE_DIR = Path(__file__).resolve().parent
    APP_HOME_DIR = RESOURCE_DIR

# 应用基本信息
APP_NAME = "番茄钟"
WINDOW_WIDTH = 500
WINDOW_HEIGHT = 780
MIN_WINDOW_WIDTH = 460
MIN_WINDOW_HEIGHT = 720
MINI_WINDOW_WIDTH = 310
MINI_WINDOW_HEIGHT = 145

# 默认时长与长休息配置（单位：分钟 / 轮数）
DEFAULT_FOCUS_MINUTES = 25
DEFAULT_BREAK_MINUTES = 5
DEFAULT_LONG_BREAK_MINUTES = 15
DEFAULT_LONG_BREAK_INTERVAL = 4
MIN_DURATION_MINUTES = 1
MAX_DURATION_MINUTES = 180
MIN_INTERVAL_COUNT = 1
MAX_INTERVAL_COUNT = 20

# 本地数据与资源路径
BASE_DIR = APP_HOME_DIR
DATA_DIR = APP_HOME_DIR / "data"
HISTORY_FILE = DATA_DIR / "task_history.json"
SOUNDS_DIR = DATA_DIR / "sounds"

ASSETS_DIR = RESOURCE_DIR / "assets"
ICON_ICO_PATH = ASSETS_DIR / "pomodoro.ico"
ICON_PNG_PATH = ASSETS_DIR / "pomodoro.png"

# 字体配置（倒计时数字使用等宽字体避免跳动）
FONT_FAMILY = "Microsoft YaHei UI"
TIMER_FONT_FAMILY = "Consolas"

# 主题配色（支持深色/浅色模式元组，CustomTkinter 会自动按当前外观选择）
COLORS = {
    "bg": ("#F4F4F5", "#18181B"),
    "card": ("#FFFFFF", "#27272A"),
    "card_border": ("#E4E4E7", "#3F3F46"),
    "subtle_bg": ("#F4F4F5", "#1F1F23"),
    "text_primary": ("#18181B", "#F4F4F5"),
    "text_secondary": ("#71717A", "#A1A1AA"),
    "focus_primary": "#EF4444",
    "focus_hover": "#DC2626",
    "break_primary": "#10B981",
    "break_hover": "#059669",
    "long_break_primary": "#8B5CF6",
    "long_break_hover": "#7C3AED",
    "accent_blue": "#3B82F6",
    "accent_blue_hover": "#2563EB",
    "neutral_btn": ("#E4E4E7", "#3F3F46"),
    "neutral_btn_hover": ("#D4D4D8", "#52525B"),
    "neutral_btn_text": ("#18181B", "#F4F4F5"),
    "success_text": "#10B981",
    "error_text": "#EF4444",
    "chart_bar": ("#F87171", "#EF4444"),
    "chart_bar_muted": ("#93C5FD", "#3B82F6"),
}
