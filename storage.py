"""
记录存储模块 — RecordStore 接口 + 两个适配器 + Excel 导出

RecordStore 隐藏了文件系统细节：目录结构、文件命名、JSON 序列化、
损坏文件恢复。调用者只注入一个实例，不直接操作 os / json / open。
"""

import json
import os
from abc import ABC, abstractmethod

import pandas as pd

from utils import now_cn


# ---------------------------------------------------------------------------
# 接口
# ---------------------------------------------------------------------------
class RecordStore(ABC):
    """记录持久化的接缝。一个适配器 = 假设性；两个 = 真实。"""

    @abstractmethod
    def save(self, record: dict) -> str:
        """持久化一条值班记录，返回存储路径（用于展示）"""
        ...

    @abstractmethod
    def list_all(self) -> list[str]:
        """返回所有记录文件名，按时间倒序"""
        ...

    @abstractmethod
    def load(self, filename: str) -> dict:
        """按文件名加载单条记录。文件损坏时抛出异常交由调用方处理。"""
        ...

    @abstractmethod
    def save_attachment(self, file, record_id: str) -> str | None:
        """保存上传的附件到该记录对应的目录，返回路径。调用方负责校验。"""
        ...

    @abstractmethod
    def excel_exists(self) -> bool:
        """Excel 汇总文件是否存在"""
        ...

    @abstractmethod
    def excel_bytes(self):
        """返回 Excel 文件的二进制内容（用于下载）"""
        ...


# ---------------------------------------------------------------------------
# 磁盘适配器
# ---------------------------------------------------------------------------
class DiskRecordStore(RecordStore):
    """本地文件系统适配器。JSON 文件存于 data_dir/，附件存于 upload_dir/。"""

    def __init__(self, data_dir: str, upload_dir: str):
        self._data_dir = data_dir
        self._upload_dir = upload_dir
        os.makedirs(self._data_dir, exist_ok=True)
        os.makedirs(self._upload_dir, exist_ok=True)

    # ---- 记录 ----

    def save(self, record: dict) -> str:
        filename = f"{record['date']}_{record['shift']}_{record['id']}.json"
        filepath = os.path.join(self._data_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        return filepath

    def list_all(self) -> list[str]:
        return sorted(
            [f for f in os.listdir(self._data_dir) if f.endswith(".json")],
            reverse=True,
        )

    def load(self, filename: str) -> dict:
        filepath = os.path.join(self._data_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    # ---- 附件 ----

    def save_attachment(self, file, record_id: str) -> str | None:
        if file is None:
            return None
        dir_path = os.path.join(self._upload_dir, record_id)
        os.makedirs(dir_path, exist_ok=True)
        safe_name = os.path.basename(file.name)
        filename = f"{now_cn().strftime('%H%M%S')}_{safe_name}"
        filepath = os.path.join(dir_path, filename)
        if not os.path.abspath(filepath).startswith(os.path.abspath(self._upload_dir)):
            return None
        with open(filepath, "wb") as f:
            f.write(file.getbuffer())
        return filepath

    # ---- Excel ----

    def excel_exists(self) -> bool:
        return os.path.exists(os.path.join(self._data_dir, "duty_logs.xlsx"))

    def excel_bytes(self) -> bytes:
        with open(os.path.join(self._data_dir, "duty_logs.xlsx"), "rb") as f:
            return f.read()


# ---------------------------------------------------------------------------
# 内存适配器（测试用）
# ---------------------------------------------------------------------------
class MemoryRecordStore(RecordStore):
    """基于 dict 的内存存储，测试不需要临时目录。"""

    def __init__(self):
        self._records: dict[str, dict] = {}
        self._attachments: dict[str, list[str]] = {}
        self._excel_bytes: bytes = b""

    # ---- 记录 ----

    def save(self, record: dict) -> str:
        filename = f"{record['date']}_{record['shift']}_{record['id']}.json"
        self._records[filename] = record
        return filename

    def list_all(self) -> list[str]:
        return sorted(self._records.keys(), reverse=True)

    def load(self, filename: str) -> dict:
        if filename not in self._records:
            raise FileNotFoundError(filename)
        return self._records[filename]

    # ---- 附件 ----

    def save_attachment(self, file, record_id: str) -> str | None:
        if file is None:
            return None
        safe_name = os.path.basename(file.name)
        fake_path = f"mem://{record_id}/{safe_name}"
        self._attachments.setdefault(record_id, []).append(fake_path)
        return fake_path

    def _set_excel_bytes(self, data: bytes):
        self._excel_bytes = data

    # ---- Excel ----

    def excel_exists(self) -> bool:
        return len(self._excel_bytes) > 0

    def excel_bytes(self) -> bytes:
        return self._excel_bytes


# ---------------------------------------------------------------------------
# Excel 导出（独立函数，只用 RecordStore 公共接口）
# ---------------------------------------------------------------------------
def rebuild_excel_from_store(store: RecordStore) -> str:
    """从 store 中的所有 JSON 记录重建 Excel，写入 store 管理的目录。

    返回 Excel 文件路径（DiskRecordStore）或空字符串（MemoryRecordStore）。
    """
    rows = []
    for fname in store.list_all():
        try:
            rec = store.load(fname)
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

    if isinstance(store, DiskRecordStore):
        excel_path = os.path.join(store._data_dir, "duty_logs.xlsx")
        df.to_excel(excel_path, index=False, engine="openpyxl")
        return excel_path
    else:
        # MemoryRecordStore：不写磁盘，存 bytes 以供验证
        from io import BytesIO
        buf = BytesIO()
        df.to_excel(buf, index=False, engine="openpyxl")
        store._set_excel_bytes(buf.getvalue())
        return ""
