"""专注任务历史记录的本地 JSON 持久化与统计模块。"""

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
import json
from pathlib import Path
import uuid

from config import HISTORY_FILE

_WEEKDAY_CN = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")


@dataclass
class TaskRecord:
    """单条已完成专注任务的记录结构。"""

    id: str
    task_name: str
    duration_minutes: int
    completed_at: str


class TaskStorage:
    """负责任务完成记录的本地读取、写入与多维度统计。"""

    def __init__(self, file_path: Path = HISTORY_FILE) -> None:
        self.file_path = Path(file_path)

    def _load_raw(self) -> list[dict]:
        """从 JSON 文件加载原始记录列表，文件缺失或损坏时返回空列表。"""
        if not self.file_path.exists():
            return []
        try:
            content = self.file_path.read_text(encoding="utf-8")
            data = json.loads(content)
            if isinstance(data, list):
                return data
            return []
        except (OSError, json.JSONDecodeError):
            return []

    def _save_raw(self, records: list[dict]) -> None:
        """将记录列表写入 JSON 文件，必要时自动创建父目录。"""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(
            json.dumps(records, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def add_record(self, task_name: str, duration_minutes: int) -> dict:
        """新增一条专注完成记录并持久化。"""
        clean_name = task_name.strip() if task_name else ""
        if not clean_name:
            clean_name = "未命名专注"

        record = TaskRecord(
            id=uuid.uuid4().hex[:8],
            task_name=clean_name,
            duration_minutes=int(duration_minutes),
            completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        record_dict = asdict(record)

        records = self._load_raw()
        records.insert(0, record_dict)
        self._save_raw(records)
        return record_dict

    def get_records(self, limit: int = 50) -> list[dict]:
        """按时间倒序获取最近的任务记录。"""
        records = self._load_raw()
        records.sort(key=lambda item: item.get("completed_at", ""), reverse=True)
        if limit > 0:
            return records[:limit]
        return records

    def get_today_stats(self) -> dict:
        """统计今日完成的番茄钟数量与总专注分钟数。"""
        today_prefix = datetime.now().strftime("%Y-%m-%d")
        records = self._load_raw()
        today_records = [
            item
            for item in records
            if str(item.get("completed_at", "")).startswith(today_prefix)
        ]
        total_minutes = sum(int(item.get("duration_minutes", 0)) for item in today_records)
        return {
            "count": len(today_records),
            "total_minutes": total_minutes,
        }

    def get_daily_stats(self, days: int = 7) -> list[dict]:
        """返回最近 N 天（含今天）的每日完成番茄数与专注分钟数列表。"""
        safe_days = max(1, int(days))
        today = datetime.now().date()
        records = self._load_raw()

        by_date: dict[str, dict[str, int]] = {}
        for item in records:
            raw_time = str(item.get("completed_at", ""))
            date_key = raw_time[:10]
            if len(date_key) == 10:
                bucket = by_date.setdefault(date_key, {"count": 0, "total_minutes": 0})
                bucket["count"] += 1
                bucket["total_minutes"] += int(item.get("duration_minutes", 0))

        result: list[dict] = []
        for offset in range(safe_days - 1, -1, -1):
            day_date = today - timedelta(days=offset)
            date_str = day_date.strftime("%Y-%m-%d")
            bucket = by_date.get(date_str, {"count": 0, "total_minutes": 0})
            result.append(
                {
                    "date": date_str,
                    "short_date": day_date.strftime("%m/%d"),
                    "weekday": _WEEKDAY_CN[day_date.weekday()],
                    "is_today": day_date == today,
                    "count": bucket["count"],
                    "total_minutes": bucket["total_minutes"],
                }
            )
        return result

    def get_summary_stats(self) -> dict:
        """返回今日、近 7 日与历史累计的汇总统计数据。"""
        records = self._load_raw()
        today = datetime.now().date()
        today_str = today.strftime("%Y-%m-%d")
        week_start_str = (today - timedelta(days=6)).strftime("%Y-%m-%d")

        today_count = 0
        today_minutes = 0
        week_count = 0
        week_minutes = 0
        total_count = 0
        total_minutes = 0

        for item in records:
            minutes = int(item.get("duration_minutes", 0))
            date_key = str(item.get("completed_at", ""))[:10]
            total_count += 1
            total_minutes += minutes
            if len(date_key) == 10:
                if date_key == today_str:
                    today_count += 1
                    today_minutes += minutes
                if week_start_str <= date_key <= today_str:
                    week_count += 1
                    week_minutes += minutes

        return {
            "today_count": today_count,
            "today_minutes": today_minutes,
            "week_count": week_count,
            "week_minutes": week_minutes,
            "total_count": total_count,
            "total_minutes": total_minutes,
        }

    def clear_records(self) -> None:
        """清空所有本地任务记录。"""
        self._save_raw([])
