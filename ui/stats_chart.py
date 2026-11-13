"""近 7 日专注统计图表与汇总卡片组件。"""

import tkinter as tk

import customtkinter as ctk

from config import COLORS, FONT_FAMILY


class StatsChartFrame(ctk.CTkFrame):
    """包含汇总统计卡片与近 7 日自适应柱状图的组件。"""

    def __init__(self, master: ctk.CTkBaseClass, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._daily_stats: list[dict] = []
        self._summary_stats: dict = {
            "today_count": 0,
            "today_minutes": 0,
            "week_count": 0,
            "week_minutes": 0,
            "total_count": 0,
            "total_minutes": 0,
        }
        self._metric_mode: str = "minutes"  # "minutes" 或 "count"

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_summary_bar()
        self._build_chart_canvas()

    def _build_summary_bar(self) -> None:
        """构建顶部汇总卡片与指标切换按钮。"""
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.grid(row=0, column=0, padx=4, pady=(2, 8), sticky="ew")
        top_bar.grid_columnconfigure((0, 1, 2), weight=1)

        self.today_value_lbl = self._create_stat_box(top_bar, 0, "今日专注")
        self.week_value_lbl = self._create_stat_box(top_bar, 1, "近 7 日")
        self.total_value_lbl = self._create_stat_box(top_bar, 2, "累计总计")

        self.metric_btn = ctk.CTkButton(
            top_bar,
            text="按分钟",
            width=66,
            height=34,
            corner_radius=8,
            font=(FONT_FAMILY, 11, "bold"),
            fg_color=COLORS["neutral_btn"],
            hover_color=COLORS["neutral_btn_hover"],
            text_color=COLORS["neutral_btn_text"],
            command=self._toggle_metric,
        )
        self.metric_btn.grid(row=0, column=3, padx=(6, 0), sticky="ns")

    def _create_stat_box(self, parent: ctk.CTkFrame, column: int, title: str) -> ctk.CTkLabel:
        """创建单个汇总统计小卡片并返回数值标签引用。"""
        box = ctk.CTkFrame(
            parent,
            fg_color=COLORS["subtle_bg"],
            corner_radius=8,
        )
        box.grid(row=0, column=column, padx=(0 if column == 0 else 4, 0), sticky="ew")

        title_lbl = ctk.CTkLabel(
            box,
            text=title,
            font=(FONT_FAMILY, 10),
            text_color=COLORS["text_secondary"],
        )
        title_lbl.pack(anchor="w", padx=8, pady=(4, 0))

        value_lbl = ctk.CTkLabel(
            box,
            text="0 分钟",
            font=(FONT_FAMILY, 12, "bold"),
            text_color=COLORS["text_primary"],
        )
        value_lbl.pack(anchor="w", padx=8, pady=(0, 4))
        return value_lbl

    def _build_chart_canvas(self) -> None:
        """构建中部柱状图 Canvas 容器。"""
        canvas_wrap = ctk.CTkFrame(
            self,
            fg_color=COLORS["subtle_bg"],
            corner_radius=10,
        )
        canvas_wrap.grid(row=1, column=0, padx=4, pady=(0, 2), sticky="nsew")
        canvas_wrap.grid_columnconfigure(0, weight=1)
        canvas_wrap.grid_rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            canvas_wrap,
            highlightthickness=0,
            bd=0,
            height=130,
        )
        self.canvas.grid(row=0, column=0, padx=6, pady=6, sticky="nsew")
        self.canvas.bind("<Configure>", lambda _event: self.redraw())

    def _toggle_metric(self) -> None:
        """在显示专注分钟数与完成番茄数之间切换。"""
        if self._metric_mode == "minutes":
            self._metric_mode = "count"
            self.metric_btn.configure(text="按番茄数")
        else:
            self._metric_mode = "minutes"
            self.metric_btn.configure(text="按分钟")
        self.redraw()

    def refresh_chart(self, daily_stats: list[dict], summary_stats: dict) -> None:
        """更新数据并重绘汇总卡片与柱状图。"""
        self._daily_stats = list(daily_stats)
        self._summary_stats = dict(summary_stats)

        self.today_value_lbl.configure(
            text=f"{summary_stats.get('today_count', 0)} 个 / {summary_stats.get('today_minutes', 0)} 分"
        )
        self.week_value_lbl.configure(
            text=f"{summary_stats.get('week_count', 0)} 个 / {summary_stats.get('week_minutes', 0)} 分"
        )
        self.total_value_lbl.configure(
            text=f"{summary_stats.get('total_count', 0)} 个 / {summary_stats.get('total_minutes', 0)} 分"
        )
        self.redraw()

    def redraw(self) -> None:
        """根据当前外观模式与画布尺寸重新绘制柱状图。"""
        canvas = self.canvas
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width < 40 or height < 40:
            return

        is_dark = ctk.get_appearance_mode().lower() == "dark"
        bg_color = "#1F1F23" if is_dark else "#F4F4F5"
        grid_color = "#3F3F46" if is_dark else "#D4D4D8"
        text_color = "#E4E4E7" if is_dark else "#27272A"
        muted_text = "#A1A1AA" if is_dark else "#71717A"
        today_bar_color = "#EF4444"
        normal_bar_color = "#3B82F6" if is_dark else "#60A5FA"
        empty_bar_color = "#2E2E34" if is_dark else "#E4E4E7"

        canvas.configure(bg=bg_color)
        canvas.delete("all")

        if not self._daily_stats:
            canvas.create_text(
                width / 2,
                height / 2,
                text="暂无统计数据",
                fill=muted_text,
                font=(FONT_FAMILY, 10),
            )
            return

        pad_left = 14
        pad_right = 14
        pad_top = 22
        pad_bottom = 34
        plot_w = max(40, width - pad_left - pad_right)
        plot_h = max(30, height - pad_top - pad_bottom)

        metric_key = "total_minutes" if self._metric_mode == "minutes" else "count"
        unit = "分" if self._metric_mode == "minutes" else "个"
        values = [int(item.get(metric_key, 0)) for item in self._daily_stats]
        max_val = max(values) if any(values) else 1

        # 绘制 3 条水平参考虚线
        for ratio in (0.33, 0.66, 1.0):
            y = pad_top + plot_h * (1.0 - ratio)
            canvas.create_line(
                pad_left,
                y,
                width - pad_right,
                y,
                fill=grid_color,
                dash=(3, 3),
            )

        # 基线
        base_y = pad_top + plot_h
        canvas.create_line(pad_left, base_y, width - pad_right, base_y, fill=grid_color)

        count = len(self._daily_stats)
        slot_w = plot_w / count
        bar_w = max(14, min(32, slot_w * 0.48))

        for idx, item in enumerate(self._daily_stats):
            val = values[idx]
            cx = pad_left + slot_w * (idx + 0.5)
            x1 = cx - bar_w / 2
            x2 = cx + bar_w / 2

            if val > 0:
                bar_h = max(6, (val / max_val) * (plot_h - 4))
                y1 = base_y - bar_h
                bar_color = today_bar_color if item.get("is_today") else normal_bar_color
                self._draw_rounded_top_bar(canvas, x1, y1, x2, base_y, bar_color)
                canvas.create_text(
                    cx,
                    y1 - 9,
                    text=f"{val}{unit}",
                    fill=text_color,
                    font=(FONT_FAMILY, 8, "bold"),
                )
            else:
                canvas.create_rectangle(
                    x1,
                    base_y - 3,
                    x2,
                    base_y,
                    fill=empty_bar_color,
                    outline="",
                )

            # 底部星期与日期标签
            day_label = "今日" if item.get("is_today") else str(item.get("weekday", ""))
            date_label = str(item.get("short_date", ""))
            label_color = today_bar_color if item.get("is_today") else text_color
            canvas.create_text(
                cx,
                base_y + 11,
                text=day_label,
                fill=label_color,
                font=(FONT_FAMILY, 8, "bold" if item.get("is_today") else "normal"),
            )
            canvas.create_text(
                cx,
                base_y + 24,
                text=date_label,
                fill=muted_text,
                font=(FONT_FAMILY, 7),
            )

    @staticmethod
    def _draw_rounded_top_bar(
        canvas: tk.Canvas,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        color: str,
    ) -> None:
        """在 Canvas 上绘制顶部圆角柱状条。"""
        radius = min(6.0, (x2 - x1) / 2.0, max(0.0, y2 - y1))
        if radius < 2.0 or (y2 - y1) <= radius + 1.0:
            canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="")
            return

        # 主体矩形 + 顶部两侧小圆角填充
        canvas.create_rectangle(x1, y1 + radius, x2, y2, fill=color, outline="")
        canvas.create_rectangle(x1 + radius, y1, x2 - radius, y1 + radius, fill=color, outline="")
        canvas.create_oval(x1, y1, x1 + 2 * radius, y1 + 2 * radius, fill=color, outline="")
        canvas.create_oval(x2 - 2 * radius, y1, x2, y1 + 2 * radius, fill=color, outline="")
