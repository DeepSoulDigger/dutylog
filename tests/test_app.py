"""值班日志系统单元测试"""

import json
import os
import sys
from datetime import date, timezone, timedelta
from io import BytesIO

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import (
    build_record,
    generate_report_text,
    current_shift_label,
    INSPECTION_ITEMS,
    SHIFTS,
    TZ_CN,
)
from storage import (
    DiskRecordStore,
    MemoryRecordStore,
    rebuild_excel_from_store,
)

TZ_CN_REF = timezone(timedelta(hours=8))


# ═══════════════════════════════════════════════════════════════════════════
# fixtures
# ═══════════════════════════════════════════════════════════════════════════
@pytest.fixture
def sample_inspection():
    return {item: {"ok": True, "note": ""} for item in INSPECTION_ITEMS}


@pytest.fixture
def sample_record(sample_inspection):
    return build_record(
        record_id="abc123",
        name="张三",
        duty_date=date(2026, 4, 27),
        shift="早班 (08:00 - 14:00)",
        status="正常",
        events="系统运行正常",
        inspection=sample_inspection,
        handover="请关注磁盘空间",
        attachments=["/tmp/a.png"],
    )


@pytest.fixture
def mem_store():
    return MemoryRecordStore()


@pytest.fixture
def disk_store(tmp_path):
    data_dir = tmp_path / "data"
    upload_dir = tmp_path / "uploads"
    return DiskRecordStore(str(data_dir), str(upload_dir))


# ═══════════════════════════════════════════════════════════════════════════
# current_shift_label
# ═══════════════════════════════════════════════════════════════════════════
class TestCurrentShiftLabel:
    def test_returns_valid_shift(self):
        assert current_shift_label() in SHIFTS

    def test_morning(self, monkeypatch):
        import utils
        fake_now = __import__("datetime").datetime(2026, 4, 27, 10, 0, tzinfo=TZ_CN_REF)
        monkeypatch.setattr(utils, "now_cn", lambda: fake_now)
        assert current_shift_label() == "早班 (08:00 - 14:00)"

    def test_afternoon(self, monkeypatch):
        import utils
        fake_now = __import__("datetime").datetime(2026, 4, 27, 16, 0, tzinfo=TZ_CN_REF)
        monkeypatch.setattr(utils, "now_cn", lambda: fake_now)
        assert current_shift_label() == "中班 (14:00 - 22:00)"

    def test_night(self, monkeypatch):
        import utils
        fake_now = __import__("datetime").datetime(2026, 4, 27, 23, 0, tzinfo=TZ_CN_REF)
        monkeypatch.setattr(utils, "now_cn", lambda: fake_now)
        assert current_shift_label() == "夜班 (22:00 - 次日08:00)"


# ═══════════════════════════════════════════════════════════════════════════
# build_record
# ═══════════════════════════════════════════════════════════════════════════
class TestBuildRecord:
    def test_basic_fields(self, sample_record):
        assert sample_record["id"] == "abc123"
        assert sample_record["name"] == "张三"
        assert sample_record["date"] == "2026-04-27"
        assert sample_record["shift"] == "早班"
        assert sample_record["status"] == "正常"
        assert sample_record["events"] == "系统运行正常"
        assert sample_record["handover"] == "请关注磁盘空间"

    def test_uses_provided_record_id(self, sample_inspection):
        rec = build_record("myid999", "李四", date(2026, 1, 1), "夜班 (22:00 - 次日08:00)",
                           "异常", "断电", sample_inspection, "无", [])
        assert rec["id"] == "myid999"

    def test_strips_whitespace(self, sample_inspection):
        rec = build_record("id1", "王五", date(2026, 1, 1), "早班 (08:00 - 14:00)",
                           "正常", "  事件  ", sample_inspection, "  交接  ", [])
        assert rec["events"] == "事件"
        assert rec["handover"] == "交接"

    def test_filters_none_attachments(self, sample_inspection):
        rec = build_record("id2", "张三", date(2026, 1, 1), "早班 (08:00 - 14:00)",
                           "正常", "", sample_inspection, "", ["/tmp/a.png", None, "/tmp/b.jpg"])
        assert rec["attachments"] == ["/tmp/a.png", "/tmp/b.jpg"]

    def test_timezone_aware_timestamp(self, sample_record):
        assert "+08:00" in sample_record["created_at"]


# ═══════════════════════════════════════════════════════════════════════════
# generate_report_text
# ═══════════════════════════════════════════════════════════════════════════
class TestGenerateReportText:
    def test_contains_key_fields(self, sample_record):
        text = generate_report_text(sample_record)
        assert "张三" in text
        assert "2026-04-27" in text
        assert "早班" in text
        assert "正常" in text

    def test_inspection_items(self, sample_record):
        text = generate_report_text(sample_record)
        for item in INSPECTION_ITEMS:
            assert item in text

    def test_abnormal_status(self, sample_inspection):
        sample_inspection["网络"] = {"ok": False, "note": "交换机故障"}
        rec = build_record("id3", "李四", date(2026, 1, 1), "中班 (14:00 - 22:00)",
                           "异常", "网络中断", sample_inspection, "修复交换机", [])
        text = generate_report_text(rec)
        assert "异常" in text
        assert "交换机故障" in text

    def test_empty_fields_show_placeholder(self, sample_inspection):
        rec = build_record("id4", "王五", date(2026, 1, 1), "早班 (08:00 - 14:00)",
                           "正常", "", sample_inspection, "", [])
        text = generate_report_text(rec)
        assert "（无）" in text


# ═══════════════════════════════════════════════════════════════════════════
# MemoryRecordStore（内存适配器）
# ═══════════════════════════════════════════════════════════════════════════
class TestMemoryRecordStore:
    def test_save_and_load(self, mem_store, sample_record):
        mem_store.save(sample_record)
        files = mem_store.list_all()
        assert len(files) == 1
        loaded = mem_store.load(files[0])
        assert loaded["name"] == "张三"

    def test_list_all_order(self, mem_store, sample_record, sample_inspection):
        rec1 = build_record("id1", "A", date(2026, 1, 1), "早班 (08:00 - 14:00)",
                            "正常", "", sample_inspection, "", [])
        rec2 = build_record("id2", "B", date(2026, 1, 2), "早班 (08:00 - 14:00)",
                            "正常", "", sample_inspection, "", [])
        mem_store.save(rec1)
        mem_store.save(rec2)
        files = mem_store.list_all()
        # 按名称倒序：id2 排在 id1 前面
        assert files[0].startswith("2026-01-02")

    def test_load_missing_raises(self, mem_store):
        with pytest.raises(FileNotFoundError):
            mem_store.load("nonexistent.json")

    def test_save_attachment(self, mem_store):
        class FakeFile:
            name = "photo.png"
            def getbuffer(self):
                return b"fake"

        path = mem_store.save_attachment(FakeFile(), "rec01")
        assert path == "mem://rec01/photo.png"

    def test_excel_roundtrip(self, mem_store, sample_record):
        mem_store.save(sample_record)
        rebuild_excel_from_store(mem_store)
        assert mem_store.excel_exists()
        import pandas as pd
        from io import BytesIO
        df = pd.read_excel(BytesIO(mem_store.excel_bytes()))
        assert len(df) == 1
        assert df.iloc[0]["值班人"] == "张三"


# ═══════════════════════════════════════════════════════════════════════════
# DiskRecordStore（磁盘适配器）
# ═══════════════════════════════════════════════════════════════════════════
class TestDiskRecordStore:
    def test_save_creates_file(self, disk_store, sample_record):
        path = disk_store.save(sample_record)
        assert os.path.exists(path)
        assert path.endswith(".json")

    def test_load_returns_record(self, disk_store, sample_record):
        disk_store.save(sample_record)
        files = disk_store.list_all()
        rec = disk_store.load(files[0])
        assert rec["name"] == "张三"
        assert rec["id"] == "abc123"

    def test_filename_format(self, disk_store, sample_record):
        path = disk_store.save(sample_record)
        basename = os.path.basename(path)
        assert basename.startswith("2026-04-27_早班_abc123")

    def test_save_attachment_path_traversal_blocked(self, disk_store):
        class EvilFile:
            name = "../../etc/passwd"
            def getbuffer(self):
                return b"evil"

        path = disk_store.save_attachment(EvilFile(), "rec01")
        # basename 剥离了 ../..，加上 startswith 二次校验，穿越被阻断
        assert path is not None
        assert os.path.basename(path).endswith("_passwd")

    def test_save_attachment_normal(self, disk_store):
        class FakeFile:
            name = "screenshot.png"
            def getbuffer(self):
                return b"img"

        path = disk_store.save_attachment(FakeFile(), "rec01")
        assert path is not None
        assert os.path.exists(path)


# ═══════════════════════════════════════════════════════════════════════════
# rebuild_excel_from_store
# ═══════════════════════════════════════════════════════════════════════════
class TestRebuildExcelFromStore:
    def test_creates_excel(self, disk_store, sample_record):
        disk_store.save(sample_record)
        excel_path = rebuild_excel_from_store(disk_store)
        assert os.path.exists(excel_path)
        import pandas as pd
        df = pd.read_excel(excel_path)
        assert len(df) == 1
        assert df.iloc[0]["值班人"] == "张三"

    def test_handles_corrupt_json(self, disk_store, sample_record):
        disk_store.save(sample_record)
        # 直接写一个坏文件到 data 目录
        bad = os.path.join(disk_store._data_dir, "bad.json")
        with open(bad, "w") as f:
            f.write("{invalid json")
        excel_path = rebuild_excel_from_store(disk_store)
        import pandas as pd
        df = pd.read_excel(excel_path)
        assert len(df) == 1

    def test_empty_store(self, disk_store):
        excel_path = rebuild_excel_from_store(disk_store)
        import pandas as pd
        df = pd.read_excel(excel_path)
        assert len(df) == 0
