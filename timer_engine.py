"""核心倒计时状态机与业务逻辑模块（与 UI 完全解耦）。"""

from enum import Enum

from config import (
    DEFAULT_BREAK_MINUTES,
    DEFAULT_FOCUS_MINUTES,
    DEFAULT_LONG_BREAK_INTERVAL,
    DEFAULT_LONG_BREAK_MINUTES,
    MAX_DURATION_MINUTES,
    MAX_INTERVAL_COUNT,
    MIN_DURATION_MINUTES,
    MIN_INTERVAL_COUNT,
)


class TimerMode(Enum):
    """番茄钟运行模式。"""

    FOCUS = "focus"
    BREAK = "break"
    SHORT_BREAK = "break"
    LONG_BREAK = "long_break"


class TimerState(Enum):
    """计时器运行状态。"""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"


class PomodoroEngine:
    """番茄钟倒计时状态机（支持短休息与长休息周期）。"""

    def __init__(
        self,
        focus_minutes: int = DEFAULT_FOCUS_MINUTES,
        break_minutes: int = DEFAULT_BREAK_MINUTES,
        long_break_minutes: int = DEFAULT_LONG_BREAK_MINUTES,
        long_break_interval: int = DEFAULT_LONG_BREAK_INTERVAL,
    ) -> None:
        self.focus_minutes = self._validate_minutes(focus_minutes, "专注时长")
        self.break_minutes = self._validate_minutes(break_minutes, "短休息时长")
        self.long_break_minutes = self._validate_minutes(long_break_minutes, "长休息时长")
        self.long_break_interval = self._validate_interval(long_break_interval)

        self.mode: TimerMode = TimerMode.FOCUS
        self.state: TimerState = TimerState.IDLE
        self.completed_focus_count: int = 0
        self.total_seconds: int = self.focus_minutes * 60
        self.remaining_seconds: int = self.total_seconds

    @staticmethod
    def _validate_minutes(minutes: int, label: str) -> int:
        """校验分钟数是否在允许的整数范围内。"""
        if not isinstance(minutes, int) or isinstance(minutes, bool):
            raise ValueError(f"{label}必须为整数")
        if minutes < MIN_DURATION_MINUTES or minutes > MAX_DURATION_MINUTES:
            raise ValueError(
                f"{label}必须在 {MIN_DURATION_MINUTES} 到 {MAX_DURATION_MINUTES} 分钟之间"
            )
        return minutes

    @staticmethod
    def _validate_interval(interval: int) -> int:
        """校验长休息间隔轮数是否在允许范围内。"""
        if not isinstance(interval, int) or isinstance(interval, bool):
            raise ValueError("长休息间隔必须为整数")
        if interval < MIN_INTERVAL_COUNT or interval > MAX_INTERVAL_COUNT:
            raise ValueError(
                f"长休息间隔必须在 {MIN_INTERVAL_COUNT} 到 {MAX_INTERVAL_COUNT} 轮之间"
            )
        return interval

    def _get_mode_seconds(self, mode: TimerMode) -> int:
        """获取指定模式对应的总秒数。"""
        if mode == TimerMode.FOCUS:
            minutes = self.focus_minutes
        elif mode == TimerMode.LONG_BREAK:
            minutes = self.long_break_minutes
        else:
            minutes = self.break_minutes
        return minutes * 60

    def set_durations(
        self,
        focus_minutes: int,
        break_minutes: int,
        long_break_minutes: int | None = None,
        long_break_interval: int | None = None,
    ) -> None:
        """更新专注、短休息、长休息时长及间隔轮数。若处于空闲状态，同步刷新当前剩余时间。"""
        validated_focus = self._validate_minutes(focus_minutes, "专注时长")
        validated_break = self._validate_minutes(break_minutes, "短休息时长")
        validated_long = (
            self._validate_minutes(long_break_minutes, "长休息时长")
            if long_break_minutes is not None
            else self.long_break_minutes
        )
        validated_interval = (
            self._validate_interval(long_break_interval)
            if long_break_interval is not None
            else self.long_break_interval
        )

        self.focus_minutes = validated_focus
        self.break_minutes = validated_break
        self.long_break_minutes = validated_long
        self.long_break_interval = validated_interval

        if self.state == TimerState.IDLE:
            self.total_seconds = self._get_mode_seconds(self.mode)
            self.remaining_seconds = self.total_seconds

    def switch_mode(self, mode: TimerMode) -> None:
        """切换专注/短休息/长休息模式，并重置计时器为空闲状态。"""
        self.mode = mode
        self.state = TimerState.IDLE
        self.total_seconds = self._get_mode_seconds(mode)
        self.remaining_seconds = self.total_seconds

    def complete_focus_session(self) -> TimerMode:
        """记录完成一次专注并根据长休息间隔决定切换为长休息或短休息。"""
        self.completed_focus_count += 1
        if self.completed_focus_count % self.long_break_interval == 0:
            next_mode = TimerMode.LONG_BREAK
        else:
            next_mode = TimerMode.BREAK
        self.switch_mode(next_mode)
        return next_mode

    def start(self) -> bool:
        """启动或恢复计时器。"""
        if self.state == TimerState.RUNNING:
            return False
        if self.remaining_seconds <= 0:
            self.remaining_seconds = self.total_seconds
        self.state = TimerState.RUNNING
        return True

    def pause(self) -> bool:
        """暂停正在运行的计时器。"""
        if self.state != TimerState.RUNNING:
            return False
        self.state = TimerState.PAUSED
        return True

    def reset(self) -> None:
        """重置当前模式的倒计时并回到空闲状态。"""
        self.state = TimerState.IDLE
        self.total_seconds = self._get_mode_seconds(self.mode)
        self.remaining_seconds = self.total_seconds

    def tick(self) -> bool:
        """推进 1 秒倒计时。若倒计时在本秒结束则返回 True，否则返回 False。"""
        if self.state != TimerState.RUNNING:
            return False

        self.remaining_seconds = max(0, self.remaining_seconds - 1)
        if self.remaining_seconds == 0:
            self.state = TimerState.IDLE
            return True
        return False

    def get_formatted_time(self) -> str:
        """返回 MM:SS 格式的剩余时间字符串。"""
        minutes, seconds = divmod(self.remaining_seconds, 60)
        return f"{minutes:02d}:{seconds:02d}"

    def get_progress(self) -> float:
        """返回 0.0 到 1.0 之间的已完成进度比例。"""
        if self.total_seconds <= 0:
            return 0.0
        elapsed = self.total_seconds - self.remaining_seconds
        return max(0.0, min(1.0, elapsed / self.total_seconds))
