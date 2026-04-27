"""
通用值班日志填写系统 - Duty Log System
基于 Python + Streamlit 构建
"""

import html
import json
import os
import uuid
from datetime import date

import streamlit as st

from utils import (
    SHIFTS,
    INSPECTION_ITEMS,
    STATUS_OPTIONS,
    current_shift_label,
    save_uploaded_file,
    build_record,
    save_record,
    rebuild_excel,
    generate_report_text,
)

# ---------------------------------------------------------------------------
# 路径配置
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
DATA_DIR = os.path.join(BASE_DIR, "data")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

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
# 简易密码认证
# ---------------------------------------------------------------------------
def check_password():
    """Returns `True` if the user had the correct password."""
    def password_entered():
        if st.session_state["password"] == os.environ.get("DUTYLOG_PASSWORD", "dutylog123"):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("请输入访问密码", type="password", on_change=password_entered, key="password")
        st.info("首次使用默认密码：dutylog123，可通过环境变量 DUTYLOG_PASSWORD 修改")
        st.stop()
    if not st.session_state["password_correct"]:
        st.text_input("密码错误，请重新输入", type="password", on_change=password_entered, key="password")
        st.stop()

check_password()

# ---------------------------------------------------------------------------
# 自定义样式
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    .section-title {
        font-size: 1.1rem; font-weight: 600; color: #1a73e8;
        border-left: 4px solid #1a73e8; padding-left: 0.6rem; margin-bottom: 0.8rem;
    }
    .preview-box {
        background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px;
        padding: 1rem; font-family: monospace; white-space: pre-wrap;
        word-break: break-all; font-size: 0.9rem; line-height: 1.6;
    }
    @media (max-width: 768px) {
        .block-container { padding: 1rem; }
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# 侧边栏 — 历史记录查询
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("📋 值班日志系统")
    st.divider()
    st.subheader("📁 历史记录")
    history_files = sorted(
        [f for f in os.listdir(DATA_DIR) if f.endswith(".json")],
        reverse=True,
    )
    if history_files:
        selected_file = st.selectbox(
            "选择记录查看",
            history_files,
            index=None,
            placeholder="点击选择...",
        )
        if selected_file:
            try:
                with open(os.path.join(DATA_DIR, selected_file), "r", encoding="utf-8") as f:
                    hist = json.load(f)
            except (json.JSONDecodeError, OSError):
                st.error("无法读取该记录文件，文件可能已损坏。")
                st.stop()
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
    excel_path = os.path.join(DATA_DIR, "duty_logs.xlsx")
    if os.path.exists(excel_path):
        with open(excel_path, "rb") as f:
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
    errors = []
    if not name.strip():
        errors.append("请填写值班人姓名。")
    if not events.strip() and status == "异常":
        errors.append('值班状态为"异常"时，请填写核心事件记录。')
    if errors:
        for e in errors:
            st.error(e)
        st.stop()

    record_id = uuid.uuid4().hex[:12]
    saved_paths = []
    for uf in (uploaded_files or []):
        path = save_uploaded_file(uf, record_id, UPLOAD_DIR)
        if path:
            saved_paths.append(path)

    record = build_record(record_id, name, duty_date, shift, status, events, inspection, handover, saved_paths)
    json_path = save_record(record, DATA_DIR)
    excel_path = rebuild_excel(DATA_DIR)

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
        if not name.strip():
            st.warning("请至少填写值班人姓名后再生成预览。")
            st.stop()
        record_id = uuid.uuid4().hex[:12]
        saved_paths = []
        record = build_record(record_id, name, duty_date, shift, status, events, inspection, handover, saved_paths)
    else:
        record = st.session_state.last_record

    report_text = generate_report_text(record)

    st.markdown("##### 日报预览")
    st.markdown(
        f'<div class="preview-box">{html.escape(report_text)}</div>',
        unsafe_allow_html=True,
    )

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
st.caption("通用值班日志系统 v1.1  ·  Powered by Streamlit")
