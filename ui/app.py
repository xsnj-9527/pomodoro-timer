"""基于 CustomTkinter 的番茄钟主界面模块。"""

import customtkinter as ctk

from config import (
    APP_NAME,
    COLORS,
    FONT_FAMILY,
    MIN_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    TIMER_FONT_FAMILY,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from icon_helper import apply_window_icon, ensure_app_icons, set_windows_app_id
from notifier import Notifier
from shortcut_helper import create_desktop_shortcut
from storage import TaskStorage
from timer_engine import PomodoroEngine, TimerMode, TimerState
from tray_manager import TrayManager
from ui.mini_window import MiniTimerWindow
from ui.stats_chart import StatsChartFrame
from white_noise import NOISE_OPTIONS, WhiteNoisePlayer


class PomodoroApp(ctk.CTk):
    """番茄钟桌面应用主窗口。"""

    def __init__(
        self,
        engine: PomodoroEngine | None = None,
        storage: TaskStorage | None = None,
        notifier: Notifier | None = None,
        white_noise: WhiteNoisePlayer | None = None,
        enable_tray: bool = True,
    ) -> None:
        set_windows_app_id()
        super().__init__()

        # 初始化外观（默认深色现代风格）
        self._current_theme = "Dark"
        ctk.set_appearance_mode(self._current_theme)
        ctk.set_default_color_theme("blue")

        # 注入或创建核心依赖模块
        self.engine = engine or PomodoroEngine()
        self.storage = storage or TaskStorage()
        self.notifier = notifier or Notifier()
        self.white_noise = white_noise or WhiteNoisePlayer()
        self._enable_tray = enable_tray

        self._timer_job_id: str | None = None
        self._status_override: str | None = None
        self._mini_window: MiniTimerWindow | None = None
        self._tray_manager: TrayManager | None = None
        self._is_quitting = False

        # 确保专属图标就绪
        ensure_app_icons()

        self._configure_window()
        self._build_layout()
        self._setup_tray()
        self._refresh_ui()
        self._refresh_history_and_stats()

    def _configure_window(self) -> None:
        """配置主窗口标题、专属图标、尺寸、最小尺寸与屏幕居中。"""
        self.title(APP_NAME)
        self.configure(fg_color=COLORS["bg"])
        self.minsize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)

        # 计算屏幕居中坐标
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        pos_x = max(0, (screen_w - WINDOW_WIDTH) // 2)
        pos_y = max(0, (screen_h - WINDOW_HEIGHT) // 2)
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{pos_x}+{pos_y}")

        apply_window_icon(self)
        self.after(250, lambda: apply_window_icon(self))

        self.protocol("WM_DELETE_WINDOW", self._on_window_close_requested)

    def _setup_tray(self) -> None:
        """初始化并启动系统托盘图标。"""
        if not self._enable_tray:
            return
        self._tray_manager = TrayManager(
            app=self,
            on_show_main=self._show_main_window,
            on_toggle_mini=self._toggle_mini_window,
            on_start_pause=self._toggle_start_pause,
            on_reset=self._handle_reset,
            on_quit=self._quit_app,
        )
        if not self._tray_manager.start():
            self._tray_manager = None

    def _build_layout(self) -> None:
        """构建主界面所有区块。"""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)

        self._build_header()
        self._build_mode_switcher()
        self._build_timer_card()
        self._build_task_and_noise_card()
        self._build_settings_card()
        self._build_bottom_tabs()

    def _build_header(self) -> None:
        """构建顶部标题栏、今日统计与快捷工具栏。"""
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=20, pady=(14, 6), sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        # 第一行：应用标题 + 主要窗口控制按钮
        title_label = ctk.CTkLabel(
            header,
            text="🍅 番茄钟",
            font=(FONT_FAMILY, 20, "bold"),
            text_color=COLORS["text_primary"],
        )
        title_label.grid(row=0, column=0, sticky="w")

        top_actions = ctk.CTkFrame(header, fg_color="transparent")
        top_actions.grid(row=0, column=1, sticky="e")

        self.mini_btn = ctk.CTkButton(
            top_actions,
            text="📌 迷你窗",
            width=78,
            height=28,
            corner_radius=8,
            font=(FONT_FAMILY, 11),
            fg_color=COLORS["neutral_btn"],
            hover_color=COLORS["neutral_btn_hover"],
            text_color=COLORS["neutral_btn_text"],
            command=self._toggle_mini_window,
        )
        self.mini_btn.pack(side="left", padx=(0, 6))

        self.tray_btn = ctk.CTkButton(
            top_actions,
            text="📥 托盘",
            width=66,
            height=28,
            corner_radius=8,
            font=(FONT_FAMILY, 11),
            fg_color=COLORS["neutral_btn"],
            hover_color=COLORS["neutral_btn_hover"],
            text_color=COLORS["neutral_btn_text"],
            command=self._hide_to_tray,
        )
        self.tray_btn.pack(side="left", padx=(0, 6))

        self.theme_btn = ctk.CTkButton(
            top_actions,
            text="☀️ 浅色",
            width=68,
            height=28,
            corner_radius=8,
            font=(FONT_FAMILY, 11),
            fg_color=COLORS["neutral_btn"],
            hover_color=COLORS["neutral_btn_hover"],
            text_color=COLORS["neutral_btn_text"],
            command=self._toggle_theme,
        )
        self.theme_btn.pack(side="left")

        # 第二行：今日统计 + 快捷方式 & 退出按钮
        sub_row = ctk.CTkFrame(header, fg_color="transparent")
        sub_row.grid(row=1, column=0, columnspan=2, pady=(4, 0), sticky="ew")
        sub_row.grid_columnconfigure(0, weight=1)

        self.today_stats_label = ctk.CTkLabel(
            sub_row,
            text="今日完成: 0 个番茄 (0 分钟)",
            font=(FONT_FAMILY, 12),
            text_color=COLORS["text_secondary"],
        )
        self.today_stats_label.grid(row=0, column=0, sticky="w")

        sub_actions = ctk.CTkFrame(sub_row, fg_color="transparent")
        sub_actions.grid(row=0, column=1, sticky="e")

        self.shortcut_btn = ctk.CTkButton(
            sub_actions,
            text="🔗 桌面快捷方式",
            width=100,
            height=24,
            corner_radius=6,
            font=(FONT_FAMILY, 11),
            fg_color="transparent",
            hover_color=COLORS["neutral_btn_hover"],
            text_color=COLORS["text_secondary"],
            command=self._handle_create_shortcut,
        )
        self.shortcut_btn.pack(side="left", padx=(0, 4))

        self.quit_btn = ctk.CTkButton(
            sub_actions,
            text="⏻ 退出",
            width=54,
            height=24,
            corner_radius=6,
            font=(FONT_FAMILY, 11),
            fg_color="transparent",
            hover_color=COLORS["neutral_btn_hover"],
            text_color=COLORS["text_secondary"],
            command=self._quit_app,
        )
        self.quit_btn.pack(side="left")

    def _build_mode_switcher(self) -> None:
        """构建专注 / 短休息 / 长休息三段式切换选项卡。"""
        self._focus_tab_text, self._break_tab_text, self._long_break_tab_text = (
            self._get_mode_tab_labels()
        )
        self.mode_switcher = ctk.CTkSegmentedButton(
            self,
            values=[
                self._focus_tab_text,
                self._break_tab_text,
                self._long_break_tab_text,
            ],
            command=self._on_mode_change,
            height=36,
            corner_radius=10,
            font=(FONT_FAMILY, 12, "bold"),
            fg_color=COLORS["card"],
            unselected_color=COLORS["card"],
            unselected_hover_color=COLORS["neutral_btn_hover"],
            selected_color=COLORS["focus_primary"],
            selected_hover_color=COLORS["focus_hover"],
        )
        self.mode_switcher.grid(row=1, column=0, padx=20, pady=(2, 8), sticky="ew")
        self.mode_switcher.set(self._focus_tab_text)

    def _build_timer_card(self) -> None:
        """构建核心倒计时显示卡片与控制按钮区。"""
        card = ctk.CTkFrame(
            self,
            fg_color=COLORS["card"],
            border_width=1,
            border_color=COLORS["card_border"],
            corner_radius=16,
        )
        card.grid(row=2, column=0, padx=20, pady=(0, 8), sticky="ew")
        card.grid_columnconfigure(0, weight=1)

        status_row = ctk.CTkFrame(card, fg_color="transparent")
        status_row.grid(row=0, column=0, padx=20, pady=(12, 0), sticky="ew")
        status_row.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            status_row,
            text="准备专注",
            font=(FONT_FAMILY, 13, "bold"),
            text_color=COLORS["focus_primary"],
            anchor="w",
        )
        self.status_label.grid(row=0, column=0, sticky="w")

        self.cycle_label = ctk.CTkLabel(
            status_row,
            text="🍅 第 1/4 轮",
            font=(FONT_FAMILY, 11, "bold"),
            text_color=COLORS["text_secondary"],
            anchor="e",
        )
        self.cycle_label.grid(row=0, column=1, sticky="e")

        self.timer_label = ctk.CTkLabel(
            card,
            text="25:00",
            font=(TIMER_FONT_FAMILY, 62, "bold"),
            text_color=COLORS["text_primary"],
        )
        self.timer_label.grid(row=1, column=0, pady=(2, 6))

        self.progress_bar = ctk.CTkProgressBar(
            card,
            height=8,
            corner_radius=4,
            progress_color=COLORS["focus_primary"],
            fg_color=COLORS["subtle_bg"],
        )
        self.progress_bar.grid(row=2, column=0, padx=26, pady=(0, 12), sticky="ew")
        self.progress_bar.set(0.0)

        # 控制按钮组：开始 / 暂停 / 重置
        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.grid(row=3, column=0, padx=20, pady=(0, 14), sticky="ew")
        btn_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.start_btn = ctk.CTkButton(
            btn_frame,
            text="开始",
            height=38,
            corner_radius=10,
            font=(FONT_FAMILY, 14, "bold"),
            fg_color=COLORS["focus_primary"],
            hover_color=COLORS["focus_hover"],
            command=self._handle_start,
        )
        self.start_btn.grid(row=0, column=0, padx=(0, 6), sticky="ew")

        self.pause_btn = ctk.CTkButton(
            btn_frame,
            text="暂停",
            height=38,
            corner_radius=10,
            font=(FONT_FAMILY, 14, "bold"),
            fg_color=COLORS["accent_blue"],
            hover_color=COLORS["accent_blue_hover"],
            command=self._handle_pause,
        )
        self.pause_btn.grid(row=0, column=1, padx=6, sticky="ew")

        self.reset_btn = ctk.CTkButton(
            btn_frame,
            text="重置",
            height=38,
            corner_radius=10,
            font=(FONT_FAMILY, 14, "bold"),
            fg_color=COLORS["neutral_btn"],
            hover_color=COLORS["neutral_btn_hover"],
            text_color=COLORS["neutral_btn_text"],
            command=self._handle_reset,
        )
        self.reset_btn.grid(row=0, column=2, padx=(6, 0), sticky="ew")

    def _build_task_and_noise_card(self) -> None:
        """构建任务名称输入与白噪音控制卡片。"""
        card = ctk.CTkFrame(
            self,
            fg_color=COLORS["card"],
            border_width=1,
            border_color=COLORS["card_border"],
            corner_radius=12,
        )
        card.grid(row=3, column=0, padx=20, pady=(0, 8), sticky="ew")
        card.grid_columnconfigure(1, weight=1)

        # 第一行：当前任务输入
        task_lbl = ctk.CTkLabel(
            card,
            text="当前任务",
            font=(FONT_FAMILY, 12, "bold"),
            text_color=COLORS["text_primary"],
        )
        task_lbl.grid(row=0, column=0, padx=(14, 10), pady=(10, 6), sticky="w")

        self.task_entry = ctk.CTkEntry(
            card,
            placeholder_text="输入任务名称（可选，专注完成后自动记录）",
            height=32,
            corner_radius=8,
            font=(FONT_FAMILY, 12),
            fg_color=COLORS["subtle_bg"],
            border_color=COLORS["card_border"],
        )
        self.task_entry.grid(row=0, column=1, columnspan=2, padx=(0, 14), pady=(10, 6), sticky="ew")
        self.task_entry.bind("<KeyRelease>", lambda _e: self._sync_mini_window())

        # 第二行：白噪音选择与仅专注播放开关
        noise_lbl = ctk.CTkLabel(
            card,
            text="白噪音",
            font=(FONT_FAMILY, 12, "bold"),
            text_color=COLORS["text_primary"],
        )
        noise_lbl.grid(row=1, column=0, padx=(14, 10), pady=(2, 10), sticky="w")

        self.noise_menu = ctk.CTkOptionMenu(
            card,
            values=NOISE_OPTIONS,
            height=30,
            corner_radius=8,
            font=(FONT_FAMILY, 12),
            fg_color=COLORS["subtle_bg"],
            button_color=COLORS["neutral_btn"],
            button_hover_color=COLORS["neutral_btn_hover"],
            text_color=COLORS["text_primary"],
            command=self._on_noise_change,
        )
        self.noise_menu.set(NOISE_OPTIONS[0])
        self.noise_menu.grid(row=1, column=1, padx=(0, 10), pady=(2, 10), sticky="ew")

        self.noise_focus_only_var = ctk.BooleanVar(value=True)
        self.noise_focus_switch = ctk.CTkSwitch(
            card,
            text="仅专注时播放",
            variable=self.noise_focus_only_var,
            font=(FONT_FAMILY, 11),
            text_color=COLORS["text_secondary"],
            command=self._on_noise_focus_only_toggle,
        )
        self.noise_focus_switch.grid(row=1, column=2, padx=(0, 14), pady=(2, 10), sticky="e")

    def _build_settings_card(self) -> None:
        """构建自定义专注、短休息、长休息时长与间隔设置区。"""
        card = ctk.CTkFrame(
            self,
            fg_color=COLORS["card"],
            border_width=1,
            border_color=COLORS["card_border"],
            corner_radius=12,
        )
        card.grid(row=4, column=0, padx=20, pady=(0, 8), sticky="ew")
        card.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.focus_entry = self._create_setting_input(
            card, 0, "专注(分)", str(self.engine.focus_minutes)
        )
        self.break_entry = self._create_setting_input(
            card, 1, "短休(分)", str(self.engine.break_minutes)
        )
        self.long_break_entry = self._create_setting_input(
            card, 2, "长休(分)", str(self.engine.long_break_minutes)
        )
        self.interval_entry = self._create_setting_input(
            card, 3, "长休间隔", str(self.engine.long_break_interval)
        )

        self.apply_settings_btn = ctk.CTkButton(
            card,
            text="应用设置",
            width=80,
            height=30,
            corner_radius=8,
            font=(FONT_FAMILY, 12, "bold"),
            fg_color=COLORS["neutral_btn"],
            hover_color=COLORS["neutral_btn_hover"],
            text_color=COLORS["neutral_btn_text"],
            command=self._handle_apply_settings,
        )
        self.apply_settings_btn.grid(row=0, column=4, rowspan=2, padx=(6, 14), pady=(10, 4), sticky="se")

        self.settings_feedback_label = ctk.CTkLabel(
            card,
            text="时长范围 1~180 分钟 · 每 N 轮专注后进入长休息",
            font=(FONT_FAMILY, 11),
            text_color=COLORS["text_secondary"],
        )
        self.settings_feedback_label.grid(
            row=2, column=0, columnspan=5, padx=14, pady=(2, 8), sticky="w"
        )

    @staticmethod
    def _create_setting_input(
        parent: ctk.CTkFrame, column: int, label_text: str, initial_value: str
    ) -> ctk.CTkEntry:
        """创建单个竖排设置标签与输入框。"""
        lbl = ctk.CTkLabel(
            parent,
            text=label_text,
            font=(FONT_FAMILY, 11),
            text_color=COLORS["text_secondary"],
        )
        lbl.grid(row=0, column=column, padx=(12 if column == 0 else 6, 4), pady=(8, 2), sticky="w")

        entry = ctk.CTkEntry(
            parent,
            width=64,
            height=28,
            justify="center",
            font=(FONT_FAMILY, 12),
            fg_color=COLORS["subtle_bg"],
            border_color=COLORS["card_border"],
        )
        entry.insert(0, initial_value)
        entry.grid(row=1, column=column, padx=(12 if column == 0 else 6, 4), pady=(0, 2), sticky="ew")
        return entry

    def _build_bottom_tabs(self) -> None:
        """构建底部统计图表与历史记录标签页区域。"""
        self.bottom_tabs = ctk.CTkTabview(
            self,
            corner_radius=12,
            fg_color=COLORS["card"],
            border_width=1,
            border_color=COLORS["card_border"],
            segmented_button_fg_color=COLORS["subtle_bg"],
            segmented_button_selected_color=COLORS["accent_blue"],
            segmented_button_selected_hover_color=COLORS["accent_blue_hover"],
            segmented_button_unselected_color=COLORS["subtle_bg"],
            segmented_button_unselected_hover_color=COLORS["neutral_btn_hover"],
        )
        self.bottom_tabs.grid(row=5, column=0, padx=20, pady=(0, 14), sticky="nsew")

        stats_tab = self.bottom_tabs.add("📊 统计图表")
        stats_tab.grid_columnconfigure(0, weight=1)
        stats_tab.grid_rowconfigure(0, weight=1)

        self.stats_chart = StatsChartFrame(stats_tab)
        self.stats_chart.grid(row=0, column=0, sticky="nsew")

        history_tab = self.bottom_tabs.add("📝 历史记录")
        history_tab.grid_columnconfigure(0, weight=1)
        history_tab.grid_rowconfigure(1, weight=1)

        history_header = ctk.CTkFrame(history_tab, fg_color="transparent")
        history_header.grid(row=0, column=0, padx=6, pady=(2, 4), sticky="ew")
        history_header.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            history_header,
            text="已完成专注记录",
            font=(FONT_FAMILY, 12, "bold"),
            text_color=COLORS["text_primary"],
        )
        title.grid(row=0, column=0, sticky="w")

        self.clear_history_btn = ctk.CTkButton(
            history_header,
            text="清空记录",
            width=72,
            height=24,
            corner_radius=6,
            font=(FONT_FAMILY, 11),
            fg_color="transparent",
            hover_color=COLORS["neutral_btn_hover"],
            text_color=COLORS["text_secondary"],
            command=self._handle_clear_history,
        )
        self.clear_history_btn.grid(row=0, column=1, sticky="e")

        self.history_list = ctk.CTkScrollableFrame(
            history_tab,
            fg_color="transparent",
            corner_radius=8,
        )
        self.history_list.grid(row=1, column=0, padx=2, pady=(0, 4), sticky="nsew")
        self.history_list.grid_columnconfigure(0, weight=1)

    def _get_mode_tab_labels(self) -> tuple[str, str, str]:
        """生成带当前时长提示的三模式选项卡文本。"""
        return (
            f"专注 ({self.engine.focus_minutes:02d}:00)",
            f"短休息 ({self.engine.break_minutes:02d}:00)",
            f"长休息 ({self.engine.long_break_minutes:02d}:00)",
        )

    def _sync_mode_switcher_labels(self) -> None:
        """同步更新模式选项卡显示文字与当前选中项。"""
        focus_text, break_text, long_break_text = self._get_mode_tab_labels()
        self._focus_tab_text = focus_text
        self._break_tab_text = break_text
        self._long_break_tab_text = long_break_text
        self.mode_switcher.configure(values=[focus_text, break_text, long_break_text])

        if self.engine.mode == TimerMode.FOCUS:
            active_text = focus_text
        elif self.engine.mode == TimerMode.LONG_BREAK:
            active_text = long_break_text
        else:
            active_text = break_text
        self.mode_switcher.set(active_text)

    def _get_mode_colors(self) -> tuple[str, str]:
        """返回当前模式对应的主题主色与悬停色。"""
        if self.engine.mode == TimerMode.FOCUS:
            return COLORS["focus_primary"], COLORS["focus_hover"]
        if self.engine.mode == TimerMode.LONG_BREAK:
            return COLORS["long_break_primary"], COLORS["long_break_hover"]
        return COLORS["break_primary"], COLORS["break_hover"]

    def _get_mode_short_label(self) -> str:
        """返回当前模式的简短中文名称。"""
        if self.engine.mode == TimerMode.FOCUS:
            return "专注"
        if self.engine.mode == TimerMode.LONG_BREAK:
            return "长休息"
        return "短休息"

    def _get_cycle_text(self) -> str:
        """生成当前专注轮次提示文案。"""
        interval = self.engine.long_break_interval
        done = self.engine.completed_focus_count
        if self.engine.mode == TimerMode.LONG_BREAK:
            return f"☕ 长休息时刻 (已完成 {done} 轮)"
        current_round = (done % interval) + 1
        return f"🍅 第 {current_round}/{interval} 轮 · 累计 {done} 轮"

    def _toggle_theme(self) -> None:
        """切换深色与浅色外观模式并重绘统计图表。"""
        if self._current_theme == "Dark":
            self._current_theme = "Light"
            self.theme_btn.configure(text="🌙 深色")
        else:
            self._current_theme = "Dark"
            self.theme_btn.configure(text="☀️ 浅色")
        ctk.set_appearance_mode(self._current_theme)
        self.after(50, self.stats_chart.redraw)

    def _on_mode_change(self, selected_value: str) -> None:
        """响应三段式模式选项卡切换。"""
        self._cancel_timer_loop()
        self._status_override = None
        if selected_value == self._focus_tab_text:
            target_mode = TimerMode.FOCUS
        elif selected_value == self._long_break_tab_text:
            target_mode = TimerMode.LONG_BREAK
        else:
            target_mode = TimerMode.BREAK
        self.engine.switch_mode(target_mode)
        self.white_noise.sync(self.engine.mode, self.engine.state)
        self._refresh_ui()

    def _on_noise_change(self, selected_noise: str) -> None:
        """切换白噪音类型并同步播放状态。"""
        self.white_noise.set_option(selected_noise)
        self.white_noise.sync(self.engine.mode, self.engine.state)

    def _on_noise_focus_only_toggle(self) -> None:
        """切换白噪音是否仅在专注运行期间播放。"""
        self.white_noise.set_focus_only(self.noise_focus_only_var.get())
        self.white_noise.sync(self.engine.mode, self.engine.state)

    def _handle_start(self) -> None:
        """处理开始/继续按钮点击事件。"""
        self._status_override = None
        if self.engine.start():
            self.white_noise.sync(self.engine.mode, self.engine.state)
            self._refresh_ui()
            self._schedule_next_tick()

    def _handle_pause(self) -> None:
        """处理暂停按钮点击事件。"""
        self._cancel_timer_loop()
        if self.engine.pause():
            self.white_noise.sync(self.engine.mode, self.engine.state)
            self._refresh_ui()

    def _toggle_start_pause(self) -> None:
        """根据当前运行状态切换开始或暂停（供悬浮窗与托盘调用）。"""
        if self.engine.state == TimerState.RUNNING:
            self._handle_pause()
        else:
            self._handle_start()

    def _handle_reset(self) -> None:
        """处理重置按钮点击事件。"""
        self._cancel_timer_loop()
        self._status_override = None
        self.engine.reset()
        self.white_noise.sync(self.engine.mode, self.engine.state)
        self._refresh_ui()

    def _handle_apply_settings(self) -> None:
        """校验并应用用户输入的专注、短休息、长休息时长与间隔轮数。"""
        try:
            focus_val = int(self.focus_entry.get().strip())
            break_val = int(self.break_entry.get().strip())
            long_break_val = int(self.long_break_entry.get().strip())
            interval_val = int(self.interval_entry.get().strip())
            self.engine.set_durations(
                focus_val,
                break_val,
                long_break_minutes=long_break_val,
                long_break_interval=interval_val,
            )
        except ValueError as exc:
            self.settings_feedback_label.configure(
                text=f"设置无效：{exc}",
                text_color=COLORS["error_text"],
            )
            return

        self._sync_mode_switcher_labels()
        self._refresh_ui()

        if self.engine.state == TimerState.IDLE:
            msg = (
                f"已应用：专注 {focus_val}分 / 短休 {break_val}分 / "
                f"长休 {long_break_val}分 (每{interval_val}轮)"
            )
        else:
            msg = "已保存设置（当前计时重置或切换模式后生效）"
        self.settings_feedback_label.configure(text=msg, text_color=COLORS["success_text"])

    def _handle_clear_history(self) -> None:
        """清空本地历史任务记录并刷新统计图表。"""
        self.storage.clear_records()
        self._refresh_history_and_stats()

    def _handle_create_shortcut(self) -> None:
        """生成桌面快捷方式并在界面反馈结果。"""
        try:
            ok, target_path, msg = create_desktop_shortcut()
            color = COLORS["success_text"] if ok else COLORS["accent_blue"]
            self.settings_feedback_label.configure(text=msg, text_color=color)
        except Exception as exc:
            self.settings_feedback_label.configure(
                text=f"创建快捷方式失败：{exc}",
                text_color=COLORS["error_text"],
            )

    def _toggle_mini_window(self) -> None:
        """打开或关闭置顶迷你悬浮窗。"""
        if self._mini_window is not None and self._mini_window.winfo_exists():
            self._close_mini_window()
            return

        self._mini_window = MiniTimerWindow(
            master=self,
            on_start_pause=self._toggle_start_pause,
            on_reset=self._handle_reset,
            on_restore_main=self._show_main_window,
            on_close=self._close_mini_window,
        )
        self.mini_btn.configure(text="📌 关闭迷你")
        self._sync_mini_window()

    def _close_mini_window(self) -> None:
        """关闭置顶迷你悬浮窗。"""
        if self._mini_window is not None:
            try:
                if self._mini_window.winfo_exists():
                    self._mini_window.destroy()
            except Exception:
                pass
            self._mini_window = None
        self.mini_btn.configure(text="📌 迷你窗")

    def _sync_mini_window(self) -> None:
        """将当前计时状态同步刷新到置顶迷你悬浮窗。"""
        if self._mini_window is None or not self._mini_window.winfo_exists():
            return
        primary_color, hover_color = self._get_mode_colors()
        self._mini_window.update_view(
            mode_text=self._get_mode_short_label(),
            task_text=self.task_entry.get(),
            time_text=self.engine.get_formatted_time(),
            progress=self.engine.get_progress(),
            primary_color=primary_color,
            hover_color=hover_color,
            is_running=self.engine.state == TimerState.RUNNING,
            is_paused=self.engine.state == TimerState.PAUSED,
        )

    def _hide_to_tray(self) -> None:
        """隐藏主窗口到系统托盘。"""
        if self._tray_manager is not None and self._tray_manager.is_running:
            self.withdraw()
        else:
            self.iconify()

    def _show_main_window(self) -> None:
        """从系统托盘或最小化状态恢复并置前主窗口。"""
        self.deiconify()
        self.lift()
        try:
            self.focus_force()
        except Exception:
            pass

    def _on_window_close_requested(self) -> None:
        """处理点击窗口右上角关闭按钮事件：有托盘时最小化到托盘，否则直接退出。"""
        if self._tray_manager is not None and self._tray_manager.is_running:
            self._hide_to_tray()
            self._status_override = "已最小化到系统托盘（可从托盘右键彻底退出）"
            self._refresh_ui()
        else:
            self._quit_app()

    def _quit_app(self) -> None:
        """彻底退出应用并释放定时器、白噪音与托盘资源。"""
        if self._is_quitting:
            return
        self._is_quitting = True
        self.destroy()

    def _schedule_next_tick(self) -> None:
        """调度下一次 1 秒倒计时回调。"""
        self._cancel_timer_loop()
        self._timer_job_id = self.after(1000, self._on_tick)

    def _cancel_timer_loop(self) -> None:
        """取消挂起的倒计时回调。"""
        if self._timer_job_id is not None:
            try:
                self.after_cancel(self._timer_job_id)
            except Exception:
                pass
            self._timer_job_id = None

    def _on_tick(self) -> None:
        """每秒执行一次倒计时推进，并在结束时触发记录与提醒。"""
        self._timer_job_id = None
        finished = self.engine.tick()
        if finished:
            self._handle_timer_finished()
            return

        self._refresh_ui()
        if self.engine.state == TimerState.RUNNING:
            self._schedule_next_tick()

    def _handle_timer_finished(self) -> None:
        """处理单个专注/短休/长休周期结束后的记录、通知与自动模式切换。"""
        finished_mode = self.engine.mode

        if finished_mode == TimerMode.FOCUS:
            task_name = self.task_entry.get().strip() or "未命名专注"
            self.storage.add_record(task_name, self.engine.focus_minutes)
            self._refresh_history_and_stats()

            next_mode = self.engine.complete_focus_session()
            self.white_noise.sync(self.engine.mode, self.engine.state)

            if next_mode == TimerMode.LONG_BREAK:
                self.notifier.notify(
                    "专注完成 · 开启长休息！",
                    (
                        f"已完成第 {self.engine.completed_focus_count} 轮专注「{task_name}」，"
                        f"好好享受 {self.engine.long_break_minutes} 分钟长休息吧！"
                    ),
                )
                self._status_override = (
                    f"🌟 已完成 {self.engine.long_break_interval} 轮！自动切换至长休息"
                )
            else:
                self.notifier.notify(
                    "专注完成！",
                    f"已完成任务：{task_name}（{self.engine.focus_minutes} 分钟），短休息一下吧！",
                )
                self._status_override = "🎉 专注完成！已切换至短休息模式"
        else:
            self.engine.switch_mode(TimerMode.FOCUS)
            self.white_noise.sync(self.engine.mode, self.engine.state)
            self.notifier.notify(
                "休息结束！",
                "休息时间到，准备好开始新一轮专注了吗？",
            )
            self._status_override = "⚡ 休息结束！已切换回专注模式"

        self._sync_mode_switcher_labels()
        self._refresh_ui()

    def _refresh_ui(self) -> None:
        """根据引擎当前模式与状态同步刷新主界面、托盘提示与迷你悬浮窗。"""
        primary_color, hover_color = self._get_mode_colors()

        # 更新模式选择器高亮色
        self.mode_switcher.configure(
            selected_color=primary_color,
            selected_hover_color=hover_color,
        )

        # 更新状态文本与轮次指示
        if self._status_override:
            status_text = self._status_override
        elif self.engine.state == TimerState.RUNNING:
            if self.engine.mode == TimerMode.FOCUS:
                status_text = "专注进行中..."
            elif self.engine.mode == TimerMode.LONG_BREAK:
                status_text = "深度长休息中..."
            else:
                status_text = "短休息放松中..."
        elif self.engine.state == TimerState.PAUSED:
            status_text = "已暂停"
        else:
            if self.engine.mode == TimerMode.FOCUS:
                status_text = "准备专注"
            elif self.engine.mode == TimerMode.LONG_BREAK:
                status_text = "准备长休息"
            else:
                status_text = "准备短休息"

        self.status_label.configure(text=status_text, text_color=primary_color)
        self.cycle_label.configure(text=self._get_cycle_text())

        # 更新时间与进度条
        time_str = self.engine.get_formatted_time()
        self.timer_label.configure(text=time_str)
        self.progress_bar.configure(progress_color=primary_color)
        self.progress_bar.set(self.engine.get_progress())

        # 更新控制按钮可用性与文字
        state = self.engine.state
        if state == TimerState.IDLE:
            self.start_btn.configure(
                text="开始",
                state="normal",
                fg_color=primary_color,
                hover_color=hover_color,
            )
            self.pause_btn.configure(state="disabled")
        elif state == TimerState.RUNNING:
            self.start_btn.configure(
                text="运行中",
                state="disabled",
                fg_color=primary_color,
                hover_color=hover_color,
            )
            self.pause_btn.configure(state="normal")
        else:
            self.start_btn.configure(
                text="继续",
                state="normal",
                fg_color=primary_color,
                hover_color=hover_color,
            )
            self.pause_btn.configure(state="disabled")

        # 同步系统托盘提示文本
        if self._tray_manager is not None:
            self._tray_manager.update_tooltip(
                f"番茄钟 · {self._get_mode_short_label()} {time_str}"
            )

        # 同步置顶迷你悬浮窗
        self._sync_mini_window()

    def _refresh_history_and_stats(self) -> None:
        """刷新今日统计、7 日统计图表与历史完成任务列表。"""
        stats = self.storage.get_today_stats()
        self.today_stats_label.configure(
            text=f"今日完成: {stats['count']} 个番茄 ({stats['total_minutes']} 分钟)"
        )

        daily_stats = self.storage.get_daily_stats(days=7)
        summary_stats = self.storage.get_summary_stats()
        self.stats_chart.refresh_chart(daily_stats, summary_stats)

        # 清空已有历史列表项
        for widget in self.history_list.winfo_children():
            widget.destroy()

        records = self.storage.get_records(limit=30)
        if not records:
            empty_label = ctk.CTkLabel(
                self.history_list,
                text="暂无专注记录，开始你的第一个番茄钟吧！",
                font=(FONT_FAMILY, 12),
                text_color=COLORS["text_secondary"],
            )
            empty_label.grid(row=0, column=0, pady=24)
            return

        for idx, item in enumerate(records):
            row_frame = ctk.CTkFrame(
                self.history_list,
                fg_color=COLORS["subtle_bg"],
                corner_radius=8,
            )
            row_frame.grid(row=idx, column=0, padx=4, pady=4, sticky="ew")
            row_frame.grid_columnconfigure(0, weight=1)

            task_lbl = ctk.CTkLabel(
                row_frame,
                text=item.get("task_name", "未命名专注"),
                font=(FONT_FAMILY, 13, "bold"),
                text_color=COLORS["text_primary"],
                anchor="w",
            )
            task_lbl.grid(row=0, column=0, padx=(10, 6), pady=(6, 0), sticky="w")

            time_str = str(item.get("completed_at", ""))
            short_time = time_str[5:16] if len(time_str) >= 16 else time_str
            meta_lbl = ctk.CTkLabel(
                row_frame,
                text=short_time,
                font=(FONT_FAMILY, 11),
                text_color=COLORS["text_secondary"],
                anchor="w",
            )
            meta_lbl.grid(row=1, column=0, padx=(10, 6), pady=(0, 6), sticky="w")

            duration_badge = ctk.CTkLabel(
                row_frame,
                text=f"{item.get('duration_minutes', 0)} 分钟",
                font=(FONT_FAMILY, 11, "bold"),
                text_color=COLORS["focus_primary"],
            )
            duration_badge.grid(row=0, column=1, rowspan=2, padx=(6, 12), sticky="e")

    def destroy(self) -> None:
        """销毁窗口前取消挂起的定时器、停止白噪音与系统托盘。"""
        self._cancel_timer_loop()
        self.white_noise.stop()
        if self._tray_manager is not None:
            self._tray_manager.stop()
            self._tray_manager = None
        self._close_mini_window()
        super().destroy()
