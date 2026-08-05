"""
值班日志系统 — 领域逻辑模块（无副作用，可直接测试）

职责：时间/班次、记录构建、日报格式化。
不包含任何文件系统 I/O（存储见 storage.py）。
"""

from datetime import datetime, date, timezone, timedelta

TZ_CN = timezone(timedelta(hours=8))

SHIFTS = {
    "早班 (08:00 - 14:00)": "早班",
    "中班 (14:00 - 22:00)": "中班",
    "夜班 (22:00 - 次日08:00)": "夜班",
}

INSPECTION_ITEMS = ["网络", "服务器", "电力", "安防"]

STATUS_OPTIONS = ["正常", "异常"]


def now_cn() -> datetime:
    return datetime.now(TZ_CN)


def current_shift_label() -> str:
    """根据当前时间自动判断班次"""
    hour = now_cn().hour
    if 8 <= hour < 14:
        return "早班 (08:00 - 14:00)"
    elif 14 <= hour < 22:
        return "中班 (14:00 - 22:00)"
    else:
        return "夜班 (22:00 - 次日08:00)"


def build_record(
    record_id: str,
    name: str,
    duty_date: date,
    shift: str,
    status: str,
    events: str,
    inspection: dict,
    handover: str,
    attachments: list[str | None],
) -> dict:
    """构建一条值班记录字典"""
    return {
        "id": record_id,
        "name": name.strip(),
        "date": duty_date.isoformat(),
        "shift": SHIFTS[shift],
        "status": status,
        "events": events.strip(),
        "inspection": inspection,
        "handover": handover.strip(),
        "attachments": [a for a in attachments if a],
        "created_at": now_cn().isoformat(),
    }


def generate_report_text(record: dict) -> str:
    """生成适合粘贴到 IM 群的日报文本"""
    lines = [
        "━" * 28,
        "📋 值班日志",
        "━" * 28,
        f"👤 值班人：{record['name']}",
        f"📅 日　期：{record['date']}",
        f"⏰ 班　次：{record['shift']}",
        f"📊 状　态：{record['status']}",
        "",
        "【核心事件记录】",
        record["events"] if record["events"] else "（无）",
        "",
        "【设备巡检情况】",
    ]
    for item, info in record["inspection"].items():
        icon = "✅" if info["ok"] else "❌"
        note = f" — {info['note']}" if not info["ok"] and info.get("note") else ""
        lines.append(f"  {icon} {item}{note}")

    lines += [
        "",
        "【待办事项 / 交接】",
        record["handover"] if record["handover"] else "（无）",
        "",
        "━" * 28,
        f"🕐 提交时间：{record['created_at'][:19].replace('T', ' ')}",
        "━" * 28,
    ]
    return "\n".join(lines)
