"""本地合成与异步循环播放白噪音模块。"""

import math
from pathlib import Path
import random
import struct
import sys
import wave

from config import SOUNDS_DIR
from timer_engine import TimerMode, TimerState

NOISE_OPTIONS = ["关闭", "柔和白噪音", "粉红雨声", "深海褐噪音", "微风暖噪"]

_NOISE_FILE_MAP = {
    "柔和白噪音": "white_soft.wav",
    "粉红雨声": "pink_rain.wav",
    "深海褐噪音": "brown_ocean.wav",
    "微风暖噪": "breeze_warm.wav",
}


class WhiteNoisePlayer:
    """使用标准库合成无缝循环白噪音 WAV 并通过系统音频接口异步播放。"""

    def __init__(self, sounds_dir: Path = SOUNDS_DIR) -> None:
        self.sounds_dir = Path(sounds_dir)
        self.current_option: str = "关闭"
        self.focus_only: bool = True
        self.is_playing: bool = False
        self._active_file: Path | None = None

    def ensure_sound_files(self) -> dict[str, Path]:
        """确保 4 种白噪音 WAV 文件存在，缺失时自动合成 3 秒无缝循环音频。"""
        self.sounds_dir.mkdir(parents=True, exist_ok=True)
        result: dict[str, Path] = {}
        for option, filename in _NOISE_FILE_MAP.items():
            wav_path = self.sounds_dir / filename
            if not wav_path.exists():
                self._generate_noise_wav(wav_path, option)
            result[option] = wav_path
        return result

    @staticmethod
    def _generate_noise_wav(wav_path: Path, option: str) -> None:
        """合成 3 秒长、22050Hz 采样率、首尾平滑交叉淡入淡出的 16-bit 单声道 WAV。"""
        sample_rate = 22050
        duration_sec = 3
        num_samples = sample_rate * duration_sec
        fade_samples = int(sample_rate * 0.25)

        rng = random.Random(hash(option) & 0xFFFFFFFF)
        raw: list[float] = []

        # 粉红噪音状态变量（Paul Kellet 近似滤波器）
        b0 = b1 = b2 = b3 = b4 = b5 = b6 = 0.0
        # 褐噪音与低通滤波器状态
        brown = 0.0
        lp = 0.0

        for i in range(num_samples):
            white = rng.uniform(-1.0, 1.0)
            if option == "柔和白噪音":
                lp = lp * 0.65 + white * 0.35
                sample = lp * 0.22
            elif option == "粉红雨声":
                b0 = 0.99886 * b0 + white * 0.0555179
                b1 = 0.99332 * b1 + white * 0.0750759
                b2 = 0.96900 * b2 + white * 0.1538520
                b3 = 0.86650 * b3 + white * 0.3104856
                b4 = 0.55000 * b4 + white * 0.5329522
                b5 = -0.7616 * b5 - white * 0.0168980
                pink = (b0 + b1 + b2 + b3 + b4 + b5 + b6 + white * 0.5362) * 0.08
                b6 = white * 0.115926
                # 叠加轻微雨滴高频质感
                drop = white * 0.03 if rng.random() < 0.008 else 0.0
                sample = pink * 0.55 + drop
            elif option == "深海褐噪音":
                brown = (brown + 0.035 * white) / 1.035
                wave_mod = 0.72 + 0.28 * math.sin(2.0 * math.pi * (i / num_samples))
                sample = brown * 1.15 * wave_mod
            else:  # 微风暖噪
                brown = (brown + 0.06 * white) / 1.06
                lp = lp * 0.82 + white * 0.18
                sway = 0.75 + 0.25 * math.sin(2.0 * math.pi * (i / num_samples) * 2.0)
                sample = (brown * 0.7 + lp * 0.2) * sway

            raw.append(sample)

        # 首尾 0.25 秒交叉混合，消除循环拼接处的爆音
        looped = list(raw)
        for k in range(fade_samples):
            t = k / fade_samples
            # 使用余弦淡入淡出曲线保持能量平稳
            w_in = 0.5 * (1.0 - math.cos(math.pi * t))
            w_out = 1.0 - w_in
            tail_idx = num_samples - fade_samples + k
            mixed = raw[k] * w_in + raw[tail_idx] * w_out
            looped[k] = mixed
            looped[tail_idx] = raw[tail_idx] * w_in + raw[k] * w_out

        # 归一化并写入 16-bit PCM WAV
        peak = max((abs(v) for v in looped), default=1.0)
        scale = 0.32 / peak if peak > 0 else 0.32
        pcm_frames = bytearray()
        for v in looped:
            clamped = max(-0.98, min(0.98, v * scale))
            pcm_frames.extend(struct.pack("<h", int(clamped * 32767)))

        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(bytes(pcm_frames))

    def set_option(self, option: str) -> None:
        """设置当前选择的白噪音名称。"""
        if option in NOISE_OPTIONS:
            self.current_option = option
        else:
            self.current_option = "关闭"

    def set_focus_only(self, focus_only: bool) -> None:
        """设置是否仅在专注运行期间播放白噪音。"""
        self.focus_only = bool(focus_only)

    def sync(self, mode: TimerMode, state: TimerState) -> None:
        """根据计时器当前模式与状态同步白噪音播放状态。"""
        if self.current_option == "关闭":
            self.stop()
            return

        should_play = True
        if self.focus_only:
            should_play = mode == TimerMode.FOCUS and state == TimerState.RUNNING

        if not should_play:
            self.stop()
            return

        files = self.ensure_sound_files()
        wav_path = files.get(self.current_option)
        if wav_path is None:
            self.stop()
            return

        if not self.is_playing or self._active_file != wav_path:
            self._start_loop(wav_path)

    def _start_loop(self, wav_path: Path) -> None:
        """在后台异步循环播放指定 WAV 文件。"""
        self._active_file = wav_path
        self.is_playing = True
        if sys.platform.startswith("win"):
            try:
                import winsound

                winsound.PlaySound(
                    str(wav_path),
                    winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP,
                )
            except Exception:
                pass

    def stop(self) -> None:
        """停止正在播放的白噪音循环。"""
        was_playing = self.is_playing
        self.is_playing = False
        self._active_file = None
        if was_playing and sys.platform.startswith("win"):
            try:
                import winsound

                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:
                pass
