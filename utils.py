"""
值班日志系统 — 纯函数工具模块（不依赖 Streamlit 运行时，可直接测试）
"""

import html
import json
import os
import uuid
from datetime import datetime, date, timezone, timedelta

import pandas as pd

TZ_CN = timezone(timedelta(hours=8))

SHIFTS = {
    "早班 (08:00 - 14:00)": "早班",
    "中班 (14:00 - 22:00)": "中班",
    "夜班 (22:00 - 次日08:00)": "夜班",
}

INSPECTION_ITEMS = ["网络", "服务器", "电力", "安防"]


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


def save_uploaded_file(uploaded_file, record_id: str, upload_dir: str) -> str | None:
    """将上传的图片保存到本地，返回存储路径。需传入 upload_dir 以便测试。"""
    if uploaded_file is None:
        return None
    dir_path = os.path.join(upload_dir, record_id)
    os.makedirs(dir_path, exist_ok=True)
    safe_name = os.path.basename(uploaded_file.name)
    filename = f"{now_cn().strftime('%H%M%S')}_{safe_name}"
    filepath = os.path.join(dir_path, filename)
    if not os.path.abspath(filepath).startswith(os.path.abspath(upload_dir)):
        return None
    with open(filepath, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return filepath


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
        "name": name,
        "date": duty_date.isoformat(),
        "shift": SHIFTS[shift],
        "status": status,
        "events": events.strip(),
        "inspection": inspection,
        "handover": handover.strip(),
        "attachments": [a for a in attachments if a],
        "created_at": now_cn().isoformat(),
    }


def save_record(record: dict, data_dir: str) -> str:
    """将记录保存为 JSON 文件，返回文件路径"""
    filename = f"{record['date']}_{record['shift']}_{record['id']}.json"
    filepath = os.path.join(data_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    return filepath


def rebuild_excel(data_dir: str) -> str:
    """从所有 JSON 文件重建 Excel，避免并发写入问题"""
    excel_path = os.path.join(data_dir, "duty_logs.xlsx")
    rows = []
    for fname in sorted(os.listdir(data_dir)):
        if not fname.endswith(".json"):
            continue
        try:
            with open(os.path.join(data_dir, fname), "r", encoding="utf-8") as f:
                rec = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        inspection_summary = "; ".join(
            f"{k}:{'正常' if v.get('ok') else '异常(' + v.get('note', '') + ')'}"
            for k, v in rec.get("inspection", {}).items()
        )
        rows.append({
            "记录ID": rec.get("id", ""),
            "值班人": rec.get("name", ""),
            "日期": rec.get("date", ""),
            "班次": rec.get("shift", ""),
            "值班状态": rec.get("status", ""),
            "核心事件": rec.get("events", ""),
            "设备巡检": inspection_summary,
            "待办交接": rec.get("handover", ""),
            "附件数量": len(rec.get("attachments", [])),
            "记录时间": rec.get("created_at", ""),
        })
    df = pd.DataFrame(rows) if rows else pd.DataFrame()
    df.to_excel(excel_path, index=False, engine="openpyxl")
    return excel_path


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
