"""番茄钟核心模块、扩展功能与 UI 初始化自检测试。"""

from datetime import datetime, timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import wave

from icon_helper import apply_window_icon, ensure_app_icons, get_tray_image, set_windows_app_id
from notifier import Notifier
from storage import TaskStorage
from timer_engine import PomodoroEngine, TimerMode, TimerState
from ui.app import PomodoroApp
from white_noise import NOISE_OPTIONS, WhiteNoisePlayer


class TestPomodoroEngine(unittest.TestCase):
    """测试倒计时状态机与长休息周期逻辑。"""

    def test_default_state_and_formatting(self) -> None:
        engine = PomodoroEngine()
        self.assertEqual(engine.focus_minutes, 25)
        self.assertEqual(engine.break_minutes, 5)
        self.assertEqual(engine.long_break_minutes, 15)
        self.assertEqual(engine.long_break_interval, 4)
        self.assertEqual(engine.mode, TimerMode.FOCUS)
        self.assertEqual(engine.state, TimerState.IDLE)
        self.assertEqual(engine.get_formatted_time(), "25:00")
        self.assertEqual(engine.get_progress(), 0.0)

    def test_start_pause_reset_and_tick(self) -> None:
        engine = PomodoroEngine(focus_minutes=1, break_minutes=1)
        self.assertFalse(engine.pause())
        self.assertTrue(engine.start())
        self.assertEqual(engine.state, TimerState.RUNNING)

        for _ in range(59):
            self.assertFalse(engine.tick())
        self.assertEqual(engine.get_formatted_time(), "00:01")
        self.assertGreater(engine.get_progress(), 0.9)

        self.assertTrue(engine.pause())
        self.assertEqual(engine.state, TimerState.PAUSED)
        self.assertFalse(engine.tick())
        self.assertTrue(engine.start())

        self.assertTrue(engine.tick())
        self.assertEqual(engine.state, TimerState.IDLE)
        self.assertEqual(engine.remaining_seconds, 0)

        engine.reset()
        self.assertEqual(engine.get_formatted_time(), "01:00")

    def test_custom_durations_and_long_break_cycle(self) -> None:
        engine = PomodoroEngine()
        engine.set_durations(40, 10, long_break_minutes=20, long_break_interval=2)
        self.assertEqual(engine.get_formatted_time(), "40:00")

        # 第 1 轮专注完成 -> 短休息
        next_mode_1 = engine.complete_focus_session()
        self.assertEqual(next_mode_1, TimerMode.BREAK)
        self.assertEqual(engine.completed_focus_count, 1)
        self.assertEqual(engine.get_formatted_time(), "10:00")

        # 切回专注完成第 2 轮 -> 长休息
        engine.switch_mode(TimerMode.FOCUS)
        next_mode_2 = engine.complete_focus_session()
        self.assertEqual(next_mode_2, TimerMode.LONG_BREAK)
        self.assertEqual(engine.completed_focus_count, 2)
        self.assertEqual(engine.get_formatted_time(), "20:00")

        with self.assertRaises(ValueError):
            engine.set_durations(0, 5)
        with self.assertRaises(ValueError):
            engine.set_durations(25, 5, long_break_minutes=15, long_break_interval=0)


class TestTaskStorage(unittest.TestCase):
    """测试任务记录持久化与多日统计图表数据源。"""

    def test_add_get_stats_and_clear(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = TaskStorage(Path(tmp_dir) / "history.json")
            storage.add_record("编写番茄钟", 25)
            storage.add_record("", 15)

            records = storage.get_records()
            self.assertEqual(len(records), 2)
            self.assertEqual(records[0]["task_name"], "未命名专注")
            self.assertEqual(records[1]["task_name"], "编写番茄钟")

            stats = storage.get_today_stats()
            self.assertEqual(stats["count"], 2)
            self.assertEqual(stats["total_minutes"], 40)

            storage.clear_records()
            self.assertEqual(storage.get_records(), [])

    def test_daily_and_summary_stats(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            json_path = Path(tmp_dir) / "history.json"
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)
            old_day = today - timedelta(days=10)

            sample_data = [
                {
                    "id": "1",
                    "task_name": "今日任务",
                    "duration_minutes": 25,
                    "completed_at": f"{today.strftime('%Y-%m-%d')} 10:00:00",
                },
                {
                    "id": "2",
                    "task_name": "昨日任务",
                    "duration_minutes": 30,
                    "completed_at": f"{yesterday.strftime('%Y-%m-%d')} 15:00:00",
                },
                {
                    "id": "3",
                    "task_name": "十天前任务",
                    "duration_minutes": 50,
                    "completed_at": f"{old_day.strftime('%Y-%m-%d')} 09:00:00",
                },
            ]
            json_path.write_text(json.dumps(sample_data), encoding="utf-8")

            storage = TaskStorage(json_path)
            daily = storage.get_daily_stats(days=7)
            self.assertEqual(len(daily), 7)
            self.assertTrue(daily[-1]["is_today"])
            self.assertEqual(daily[-1]["count"], 1)
            self.assertEqual(daily[-1]["total_minutes"], 25)
            self.assertEqual(daily[-2]["count"], 1)
            self.assertEqual(daily[-2]["total_minutes"], 30)

            summary = storage.get_summary_stats()
            self.assertEqual(summary["today_count"], 1)
            self.assertEqual(summary["today_minutes"], 25)
            self.assertEqual(summary["week_count"], 2)
            self.assertEqual(summary["week_minutes"], 55)
            self.assertEqual(summary["total_count"], 3)
            self.assertEqual(summary["total_minutes"], 105)


class TestAssetsAndWhiteNoise(unittest.TestCase):
    """测试专属图标生成与白噪音合成播放逻辑。"""

    def test_icon_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            png_path = Path(tmp_dir) / "pomodoro.png"
            ico_path = Path(tmp_dir) / "pomodoro.ico"
            out_png, out_ico = ensure_app_icons(png_path=png_path, ico_path=ico_path)
            self.assertTrue(out_png.exists())
            self.assertTrue(out_ico.exists())
            self.assertGreater(out_png.stat().st_size, 100)
            self.assertGreater(out_ico.stat().st_size, 100)

            tray_img = get_tray_image()
            self.assertEqual(tray_img.size, (64, 64))
            set_windows_app_id()

    def test_white_noise_synthesis_and_sync(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            player = WhiteNoisePlayer(sounds_dir=Path(tmp_dir))
            files = player.ensure_sound_files()
            self.assertEqual(len(files), len(NOISE_OPTIONS) - 1)
            for wav_path in files.values():
                self.assertTrue(wav_path.exists())
                with wave.open(str(wav_path), "rb") as wf:
                    self.assertEqual(wf.getnchannels(), 1)
                    self.assertEqual(wf.getframerate(), 22050)
                    self.assertGreater(wf.getnframes(), 22050)

            with patch("winsound.PlaySound") as mock_play:
                player.set_option("粉红雨声")
                player.set_focus_only(True)
                # 空闲状态下不应播放
                player.sync(TimerMode.FOCUS, TimerState.IDLE)
                self.assertFalse(player.is_playing)

                # 专注运行中应开始播放
                player.sync(TimerMode.FOCUS, TimerState.RUNNING)
                self.assertTrue(player.is_playing)
                self.assertTrue(mock_play.called)

                # 暂停后应停止播放
                player.sync(TimerMode.FOCUS, TimerState.PAUSED)
                self.assertFalse(player.is_playing)

                # 取消“仅专注时播放”后可随时试听
                player.set_focus_only(False)
                player.sync(TimerMode.BREAK, TimerState.IDLE)
                self.assertTrue(player.is_playing)
                player.stop()
                self.assertFalse(player.is_playing)


class TestNotifierAndUI(unittest.TestCase):
    """测试提醒模块与 CustomTkinter 主界面 / 迷你窗初始化流程。"""

    def test_notifier_dispatch_mocked(self) -> None:
        notifier = Notifier()
        with (
            patch.object(notifier, "_play_sound") as mock_sound,
            patch.object(notifier, "_send_system_notification") as mock_notify,
        ):
            notifier._dispatch("测试标题", "测试内容", sound=True)
            mock_sound.assert_called_once()
            mock_notify.assert_called_once_with("测试标题", "测试内容")

    def test_ui_and_mini_window_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = TaskStorage(Path(tmp_dir) / "ui_history.json")
            storage.add_record("UI 冒烟测试", 25)
            player = WhiteNoisePlayer(sounds_dir=Path(tmp_dir) / "sounds")

            app = PomodoroApp(
                storage=storage,
                white_noise=player,
                enable_tray=False,
            )

            def _exercise_ui() -> None:
                apply_window_icon(app)
                self.assertTrue(hasattr(app, "_icon_photo_refs"))
                self.assertEqual(len(app._icon_photo_refs), 2)
                app._toggle_mini_window()
                self.assertIsNotNone(app._mini_window)
                self.assertTrue(app._mini_window.winfo_exists())
                app._toggle_theme()
                app._toggle_mini_window()
                self.assertIsNone(app._mini_window)
                app.destroy()

            app.after(180, _exercise_ui)
            app.mainloop()


if __name__ == "__main__":
    unittest.main()
