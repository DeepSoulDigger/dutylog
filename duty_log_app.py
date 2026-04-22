"""
通用值班日志填写系统 - Duty Log System
基于 Python + Streamlit 构建
"""

import os
import json
import uuid
from datetime import datetime, date, timedelta

import streamlit as st
import pandas as pd

# ---------------------------------------------------------------------------
# 路径配置
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
DATA_DIR = os.path.join(BASE_DIR, "data")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
SHIFTS = {
    "早班 (08:00 - 14:00)": "早班",
    "中班 (14:00 - 22:00)": "中班",
    "夜班 (22:00 - 次日08:00)": "夜班",
}

INSPECTION_ITEMS = ["网络", "服务器", "电力", "安防"]

STATUS_OPTIONS = ["正常", "异常"]

# ---------------------------------------------------------------------------
# 页面配置（必须是第一个 Streamlit 命令）
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="值班日志系统",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# 自定义样式
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    /* 全局 */
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }

    /* 卡片 */
    .card {
        background: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }

    /* 分组标题 */
    .section-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #1a73e8;
        border-left: 4px solid #1a73e8;
        padding-left: 0.6rem;
        margin-bottom: 0.8rem;
    }

    /* 预览区域 */
    .preview-box {
        background: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 1rem;
        font-family: monospace;
        white-space: pre-wrap;
        word-break: break-all;
        font-size: 0.9rem;
        line-height: 1.6;
    }

    /* 状态标签 */
    .tag-ok {
        display: inline-block;
        background: #e6f4ea;
        color: #137333;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 500;
    }
    .tag-err {
        display: inline-block;
        background: #fce8e6;
        color: #c5221f;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 500;
    }

    /* 移动端适配 */
    @media (max-width: 768px) {
        .block-container { padding: 1rem; }
        .card { padding: 1rem; }
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------
def current_shift_label() -> str:
    """根据当前时间自动判断班次"""
    hour = datetime.now().hour
    if 8 <= hour < 14:
        return "早班 (08:00 - 14:00)"
    elif 14 <= hour < 22:
        return "中班 (14:00 - 22:00)"
    else:
        return "夜班 (22:00 - 次日08:00)"


def save_uploaded_file(uploaded_file, record_id: str) -> str | None:
    """将上传的图片保存到本地 uploads/<record_id>/ 目录，返回存储路径"""
    if uploaded_file is None:
        return None
    dir_path = os.path.join(UPLOAD_DIR, record_id)
    os.makedirs(dir_path, exist_ok=True)
    # 用时间戳+原文件名避免冲突
    filename = f"{datetime.now().strftime('%H%M%S')}_{uploaded_file.name}"
    filepath = os.path.join(dir_path, filename)
    with open(filepath, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return filepath


def build_record(
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
        "id": uuid.uuid4().hex[:12],
        "name": name,
        "date": duty_date.isoformat(),
        "shift": SHIFTS[shift],
        "status": status,
        "events": events.strip(),
        "inspection": inspection,
        "handover": handover.strip(),
        "attachments": [a for a in attachments if a],
        "created_at": datetime.now().isoformat(),
    }


def save_record(record: dict) -> str:
    """将记录保存为 JSON 文件，返回文件路径"""
    filename = f"{record['date']}_{record['shift']}_{record['id']}.json"
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    return filepath


def save_excel(record: dict) -> str:
    """将记录追加到 Excel 文件，返回文件路径"""
    excel_path = os.path.join(DATA_DIR, "duty_logs.xlsx")
    inspection_summary = "; ".join(
        f"{k}:{'正常' if v['ok'] else '异常(' + v.get('note', '') + ')'}"
        for k, v in record["inspection"].items()
    )
    row = {
        "记录ID": record["id"],
        "值班人": record["name"],
        "日期": record["date"],
        "班次": record["shift"],
        "值班状态": record["status"],
        "核心事件": record["events"],
        "设备巡检": inspection_summary,
        "待办交接": record["handover"],
        "附件数量": len(record["attachments"]),
        "记录时间": record["created_at"],
    }

    if os.path.exists(excel_path):
        df = pd.read_excel(excel_path)
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    else:
        df = pd.DataFrame([row])

    df.to_excel(excel_path, index=False, engine="openpyxl")
    return excel_path


def generate_report_text(record: dict) -> str:
    """生成适合粘贴到 IM 群的日报文本"""
    lines = [
        "━" * 28,
        f"📋 值班日志",
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


# ---------------------------------------------------------------------------
# 侧边栏 — 历史记录查询
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("📋 值班日志系统")
    st.divider()
    st.subheader("📁 历史记录")
    history_files = sorted(
        [f for f in os.listdir(DATA_DIR) if f.endswith(".json")], reverse=True
    )
    if history_files:
        selected_file = st.selectbox(
            "选择记录查看",
            history_files,
            index=None,
            placeholder="点击选择...",
        )
        if selected_file:
            with open(os.path.join(DATA_DIR, selected_file), "r", encoding="utf-8") as f:
                hist = json.load(f)
            st.json(hist)
            st.download_button(
                "⬇️ 下载该记录 JSON",
                data=json.dumps(hist, ensure_ascii=False, indent=2),
                file_name=selected_file,
                mime="application/json",
            )
    else:
        st.info("暂无历史记录。")

    st.divider()
    if os.path.exists(os.path.join(DATA_DIR, "duty_logs.xlsx")):
        with open(os.path.join(DATA_DIR, "duty_logs.xlsx"), "rb") as f:
            st.download_button(
                "📊 下载全部记录 (Excel)",
                data=f.read(),
                file_name="duty_logs.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

# ---------------------------------------------------------------------------
# 主页面
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">📝 值班日志填写</div>', unsafe_allow_html=True)

# ---- 1. 身份登记 ----
with st.container():
    st.markdown("#### 🧑‍💼 身份登记")
    col1, col2, col3 = st.columns([2, 2, 3])
    with col1:
        name = st.text_input("值班人姓名", placeholder="请输入姓名")
    with col2:
        duty_date = st.date_input("值班日期", value=date.today())
    with col3:
        shift = st.selectbox(
            "班次",
            options=list(SHIFTS.keys()),
            index=list(SHIFTS.keys()).index(current_shift_label()),
        )

st.divider()

# ---- 2. 值班状态 & 核心事件 ----
col_status, col_empty = st.columns([1, 3])
with col_status:
    status = st.selectbox("值班状态", STATUS_OPTIONS)
with col_empty:
    pass

st.markdown("#### 📌 核心事件记录")
events = st.text_area(
    "记录值班期间发生的重点事项",
    height=150,
    placeholder="请描述值班期间发生的重要事件、处理过程及结果……",
)

st.divider()

# ---- 3. 设备巡检 ----
st.markdown("#### 🔍 设备巡检情况")

inspection = {}
cols = st.columns(len(INSPECTION_ITEMS))
for idx, item in enumerate(INSPECTION_ITEMS):
    with cols[idx]:
        st.markdown(f"**{item}**")
        is_ok = st.checkbox(f"正常", key=f"insp_ok_{item}", value=True)
        note = ""
        if not is_ok:
            note = st.text_input(
                "异常备注", key=f"insp_note_{item}", placeholder="请描述异常情况"
            )
        inspection[item] = {"ok": is_ok, "note": note}

st.divider()

# ---- 4. 待办 / 交接 ----
st.markdown("#### 🔄 待办事项 / 交接")
handover = st.text_area(
    "记录需要下一班次跟进的工作",
    height=100,
    placeholder="需要下一班跟进的事项、待处理问题……",
)

st.divider()

# ---- 5. 附件上传 ----
st.markdown("#### 📷 附件上传（图片）")
uploaded_files = st.file_uploader(
    "支持上传多张图片",
    type=["png", "jpg", "jpeg", "gif", "bmp", "webp"],
    accept_multiple_files=True,
)

# 图片预览
if uploaded_files:
    preview_cols = st.columns(min(len(uploaded_files), 4))
    for i, uf in enumerate(uploaded_files):
        with preview_cols[i % len(preview_cols)]:
            st.image(uf, caption=uf.name, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# 操作按钮区域
# ---------------------------------------------------------------------------
st.markdown("#### 🚀 操作")

col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])

# 用 session_state 缓存上一次提交的记录，供"生成日报预览"使用
if "last_record" not in st.session_state:
    st.session_state.last_record = None

with col_btn1:
    submit_btn = st.button("✅ 提交日志", type="primary", use_container_width=True)

with col_btn2:
    preview_btn = st.button("👁️ 生成日报预览", use_container_width=True)

# ---------------------------------------------------------------------------
# 提交逻辑
# ---------------------------------------------------------------------------
if submit_btn:
    # 校验
    errors = []
    if not name.strip():
        errors.append("请填写值班人姓名。")
    if not events.strip() and status == "异常":
        errors.append('值班状态为"异常"时，请填写核心事件记录。')
    if errors:
        for e in errors:
            st.error(e)
        st.stop()

    # 保存附件
    record_id = uuid.uuid4().hex[:12]
    saved_paths = []
    for uf in (uploaded_files or []):
        path = save_uploaded_file(uf, record_id)
        if path:
            saved_paths.append(path)

    # 构建并保存记录
    record = build_record(name, duty_date, shift, status, events, inspection, handover, saved_paths)
    json_path = save_record(record)
    excel_path = save_excel(record)

    st.session_state.last_record = record

    st.success("🎉 日志提交成功！")
    st.caption(f"JSON 已保存至：`{json_path}`")
    st.caption(f"Excel 已更新至：`{excel_path}`")
    if saved_paths:
        st.caption(f"附件已保存至：`{UPLOAD_DIR}/{record_id}/`")

# ---------------------------------------------------------------------------
# 日报预览逻辑
# ---------------------------------------------------------------------------
if preview_btn:
    if st.session_state.last_record is None:
        # 如果还没提交过，用当前表单数据临时构建
        if not name.strip():
            st.warning("请至少填写值班人姓名后再生成预览。")
            st.stop()
        record_id = uuid.uuid4().hex[:12]
        saved_paths = []
        record = build_record(name, duty_date, shift, status, events, inspection, handover, saved_paths)
    else:
        record = st.session_state.last_record

    report_text = generate_report_text(record)

    st.markdown("##### 日报预览")
    st.markdown(f'<div class="preview-box">{report_text}</div>', unsafe_allow_html=True)

    st.code(report_text, language=None)

    st.download_button(
        "📋 复制为文本文件下载",
        data=report_text,
        file_name=f"日报_{record['date']}_{record['shift']}.txt",
        mime="text/plain",
    )

# ---------------------------------------------------------------------------
# 页脚
# ---------------------------------------------------------------------------
st.divider()
st.caption("通用值班日志系统 v1.0  ·  Powered by Streamlit")
