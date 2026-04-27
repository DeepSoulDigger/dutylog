"""值班日志系统单元测试"""

import json
import os
import sys
from datetime import date, timezone, timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import (
    build_record,
    save_record,
    generate_report_text,
    current_shift_label,
    rebuild_excel,
    INSPECTION_ITEMS,
    SHIFTS,
    TZ_CN,
)

TZ_CN_REF = timezone(timedelta(hours=8))


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------
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
def tmp_data_dir(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return str(data_dir)


# ---------------------------------------------------------------------------
# current_shift_label
# ---------------------------------------------------------------------------
class TestCurrentShiftLabel:
    def test_returns_valid_shift(self):
        result = current_shift_label()
        assert result in SHIFTS

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


# ---------------------------------------------------------------------------
# build_record
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# save_record
# ---------------------------------------------------------------------------
class TestSaveRecord:
    def test_creates_json_file(self, sample_record, tmp_data_dir):
        path = save_record(sample_record, tmp_data_dir)
        assert os.path.exists(path)
        assert path.endswith(".json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["name"] == "张三"
        assert data["id"] == "abc123"

    def test_filename_format(self, sample_record, tmp_data_dir):
        path = save_record(sample_record, tmp_data_dir)
        basename = os.path.basename(path)
        assert basename.startswith("2026-04-27_早班_abc123.json")


# ---------------------------------------------------------------------------
# generate_report_text
# ---------------------------------------------------------------------------
class TestGenerateReportText:
    def test_contains_key_fields(self, sample_record):
        text = generate_report_text(sample_record)
        assert "张三" in text
        assert "2026-04-27" in text
        assert "早班" in text
        assert "正常" in text
        assert "系统运行正常" in text
        assert "请关注磁盘空间" in text

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


# ---------------------------------------------------------------------------
# rebuild_excel
# ---------------------------------------------------------------------------
class TestRebuildExcel:
    def test_creates_excel_from_json(self, sample_record, tmp_data_dir):
        save_record(sample_record, tmp_data_dir)
        excel_path = rebuild_excel(tmp_data_dir)
        assert os.path.exists(excel_path)
        import pandas as pd
        df = pd.read_excel(excel_path)
        assert len(df) == 1
        assert df.iloc[0]["值班人"] == "张三"

    def test_handles_corrupt_json(self, sample_record, tmp_data_dir):
        save_record(sample_record, tmp_data_dir)
        with open(os.path.join(tmp_data_dir, "bad.json"), "w") as f:
            f.write("{invalid json")
        excel_path = rebuild_excel(tmp_data_dir)
        import pandas as pd
        df = pd.read_excel(excel_path)
        assert len(df) == 1

    def test_empty_data_dir(self, tmp_data_dir):
        excel_path = rebuild_excel(tmp_data_dir)
        import pandas as pd
        df = pd.read_excel(excel_path)
        assert len(df) == 0
