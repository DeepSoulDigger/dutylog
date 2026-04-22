# 📋 通用值班日志填写系统

基于 Python + Streamlit 构建的轻量级值班日志管理系统，支持移动端访问。

## 功能特性

- **身份登记**：值班人姓名、日期、班次（早/中/夜，自动识别）
- **日志填写**：值班状态、核心事件、设备巡检、待办交接
- **附件上传**：支持多张图片上传，本地存储
- **数据导出**：JSON + Excel 双格式保存
- **日报预览**：一键生成 IM 群友好的排版文本
- **历史查询**：侧边栏浏览/下载历史记录

## 快速部署

### 方式一：Docker 部署（推荐）

```bash
# 1. 克隆仓库
git clone https://github.com/DeepSoulDigger/dutylog.git
cd dutylog

# 2. 一键启动
docker compose up -d

# 3. 访问系统
# 浏览器打开 http://服务器IP:8501
```

### 方式二：直接运行

```bash
# 1. 克隆仓库
git clone https://github.com/DeepSoulDigger/dutylog.git
cd dutylog

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动应用
streamlit run duty_log_app.py
```

## 数据存储

| 目录 | 说明 |
|------|------|
| `data/` | JSON 日志文件 + 汇总 Excel |
| `uploads/` | 上传的附件图片 |

Docker 部署时这两个目录已通过 volume 映射到宿主机，数据不会随容器丢失。

## 班次定义

| 班次 | 时间范围 |
|------|----------|
| 早班 | 08:00 - 14:00 |
| 中班 | 14:00 - 22:00 |
| 夜班 | 22:00 - 次日 08:00 |

## 技术栈

- Python 3.11
- Streamlit
- Pandas / OpenPyXL
