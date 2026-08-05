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

> 所有时间均基于 `Asia/Shanghai`（UTC+8）时区判定。

## 技术栈

- Python 3.11
- Streamlit
- Pandas / OpenPyXL

## 开发

### 项目结构

```text
dutylog/
├── duty_log_app.py       # Streamlit 主入口（UI 层）
├── utils.py              # 领域逻辑：时间/班次、记录构建、日报格式化（无副作用）
├── storage.py            # 持久化抽象：RecordStore 接口 + Disk / Memory 两个适配器
├── tests/
│   └── test_app.py       # 单元测试（pytest）
├── data/                 # 运行时生成的 JSON / Excel
├── uploads/              # 运行时上传的附件
├── Dockerfile
├── docker-compose.yml
├── requirements.txt      # 运行时依赖
└── requirements-dev.txt  # 开发与测试依赖
```

### 跑测试

```bash
# 安装测试依赖
pip install -r requirements-dev.txt

# 运行测试套件
pytest tests/ -v
```

当前共 **29** 个测试，覆盖时间判定、记录构建、日报生成、内存 / 磁盘两种存储适配器以及 Excel 重建的健壮性。

### 代码风格

- 领域逻辑（`utils.py`）保持纯函数，无文件 I/O，便于单元测试
- 所有文件系统访问都走 `RecordStore` 抽象（`storage.py`），便于替换与测试
- `MemoryRecordStore` 用于测试，避免污染真实目录

## 反馈与贡献

- **Bug 报告 / 功能建议**：使用 [Issue 模板](../../issues/new/choose) 提交
- **Pull Request**：请阅读 [PR 模板](.github/PULL_REQUEST_TEMPLATE.md)，并确保 CI 全绿