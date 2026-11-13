"""置顶迷你悬浮窗模块。"""

from collections.abc import Callable

import customtkinter as ctk

from config import (
    COLORS,
    FONT_FAMILY,
    MINI_WINDOW_HEIGHT,
    MINI_WINDOW_WIDTH,
    TIMER_FONT_FAMILY,
)
from icon_helper import apply_window_icon


class MiniTimerWindow(ctk.CTkToplevel):
    """始终置顶、支持鼠标拖拽的迷你倒计时悬浮窗。"""

    def __init__(
        self,
        master: ctk.CTk,
        on_start_pause: Callable[[], None],
        on_reset: Callable[[], None],
        on_restore_main: Callable[[], None],
        on_close: Callable[[], None],
    ) -> None:
        super().__init__(master)
        self._on_start_pause = on_start_pause
        self._on_reset = on_reset
        self._on_restore_main = on_restore_main
        self._on_close = on_close

        self._drag_offset_x = 0
        self._drag_offset_y = 0

        self._configure_window()
        self._build_layout()
        self._bind_drag_events()

    def _configure_window(self) -> None:
        """配置迷你悬浮窗尺寸、位置、置顶属性与专属图标。"""
        self.title("番茄钟 · 迷你窗")
        self.configure(fg_color=COLORS["bg"])
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # 默认定位在屏幕右上角留出边距
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        pos_x = max(20, screen_w - MINI_WINDOW_WIDTH - 32)
        pos_y = 48
        self.geometry(f"{MINI_WINDOW_WIDTH}x{MINI_WINDOW_HEIGHT}+{pos_x}+{pos_y}")

        self._apply_icon()
        self.after(250, self._apply_icon)

    def _apply_icon(self) -> None:
        """尝试为悬浮窗设置专属图标。"""
        apply_window_icon(self)

    def _build_layout(self) -> None:
        """构建迷你窗三行紧凑布局。"""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._card = ctk.CTkFrame(
            self,
            fg_color=COLORS["card"],
            border_width=1,
            border_color=COLORS["card_border"],
            corner_radius=12,
        )
        self._card.grid(row=0, column=0, padx=8, pady=8, sticky="nsew")
        self._card.grid_columnconfigure(1, weight=1)

        # 第一行：模式徽标 + 任务名 + 恢复主窗口按钮
        self.mode_badge = ctk.CTkLabel(
            self._card,
            text="专注",
            font=(FONT_FAMILY, 11, "bold"),
            text_color="#FFFFFF",
            fg_color=COLORS["focus_primary"],
            corner_radius=6,
            width=54,
            height=22,
        )
        self.mode_badge.grid(row=0, column=0, padx=(10, 6), pady=(10, 4), sticky="w")

        self.task_label = ctk.CTkLabel(
            self._card,
            text="未指定任务",
            font=(FONT_FAMILY, 11),
            text_color=COLORS["text_secondary"],
            anchor="w",
        )
        self.task_label.grid(row=0, column=1, padx=(0, 6), pady=(10, 4), sticky="ew")

        self.restore_btn = ctk.CTkButton(
            self._card,
            text="↗ 主窗口",
            width=66,
            height=24,
            corner_radius=6,
            font=(FONT_FAMILY, 11),
            fg_color=COLORS["neutral_btn"],
            hover_color=COLORS["neutral_btn_hover"],
            text_color=COLORS["neutral_btn_text"],
            command=self._on_restore_main,
        )
        self.restore_btn.grid(row=0, column=2, padx=(0, 10), pady=(10, 4), sticky="e")

        # 第二行：倒计时数字 + 快捷控制按钮
        self.timer_label = ctk.CTkLabel(
            self._card,
            text="25:00",
            font=(TIMER_FONT_FAMILY, 38, "bold"),
            text_color=COLORS["text_primary"],
            anchor="w",
        )
        self.timer_label.grid(row=1, column=0, columnspan=2, padx=(12, 8), pady=(0, 6), sticky="w")

        ctrl_box = ctk.CTkFrame(self._card, fg_color="transparent")
        ctrl_box.grid(row=1, column=2, padx=(0, 10), pady=(0, 6), sticky="e")

        self.action_btn = ctk.CTkButton(
            ctrl_box,
            text="开始",
            width=58,
            height=30,
            corner_radius=8,
            font=(FONT_FAMILY, 12, "bold"),
            fg_color=COLORS["focus_primary"],
            hover_color=COLORS["focus_hover"],
            command=self._on_start_pause,
        )
        self.action_btn.pack(side="left", padx=(0, 4))

        self.reset_btn = ctk.CTkButton(
            ctrl_box,
            text="重置",
            width=46,
            height=30,
            corner_radius=8,
            font=(FONT_FAMILY, 12),
            fg_color=COLORS["neutral_btn"],
            hover_color=COLORS["neutral_btn_hover"],
            text_color=COLORS["neutral_btn_text"],
            command=self._on_reset,
        )
        self.reset_btn.pack(side="left")

        # 第三行：细长进度条
        self.progress_bar = ctk.CTkProgressBar(
            self._card,
            height=6,
            corner_radius=3,
            progress_color=COLORS["focus_primary"],
            fg_color=COLORS["subtle_bg"],
        )
        self.progress_bar.grid(row=2, column=0, columnspan=3, padx=10, pady=(0, 10), sticky="ew")
        self.progress_bar.set(0.0)

    def _bind_drag_events(self) -> None:
        """为非按钮区域绑定左键拖拽移动窗口事件。"""
        draggable_widgets = (
            self,
            self._card,
            self.mode_badge,
            self.task_label,
            self.timer_label,
            self.progress_bar,
        )
        for widget in draggable_widgets:
            widget.bind("<ButtonPress-1>", self._start_drag)
            widget.bind("<B1-Motion>", self._on_drag)

    def _start_drag(self, event) -> None:
        """记录鼠标按下时相对窗口左上角的偏移量。"""
        self._drag_offset_x = event.x_root - self.winfo_x()
        self._drag_offset_y = event.y_root - self.winfo_y()

    def _on_drag(self, event) -> None:
        """拖动时更新悬浮窗位置。"""
        new_x = event.x_root - self._drag_offset_x
        new_y = event.y_root - self._drag_offset_y
        self.geometry(f"+{new_x}+{new_y}")

    def update_view(
        self,
        mode_text: str,
        task_text: str,
        time_text: str,
        progress: float,
        primary_color: str,
        hover_color: str,
        is_running: bool,
        is_paused: bool,
    ) -> None:
        """同步主窗口传来的实时计时状态与主题色。"""
        clean_task = task_text.strip() or "未指定任务"
        if len(clean_task) > 12:
            clean_task = clean_task[:11] + "…"

        self.mode_badge.configure(text=mode_text, fg_color=primary_color)
        self.task_label.configure(text=clean_task)
        self.timer_label.configure(text=time_text)
        self.progress_bar.configure(progress_color=primary_color)
        self.progress_bar.set(progress)

        if is_running:
            action_text = "暂停"
            btn_fg = COLORS["accent_blue"]
            btn_hover = COLORS["accent_blue_hover"]
        elif is_paused:
            action_text = "继续"
            btn_fg = primary_color
            btn_hover = hover_color
        else:
            action_text = "开始"
            btn_fg = primary_color
            btn_hover = hover_color

        self.action_btn.configure(text=action_text, fg_color=btn_fg, hover_color=btn_hover)
