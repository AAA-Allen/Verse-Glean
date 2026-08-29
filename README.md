# 影海拾光——视频平台知识胶囊提取系统

> 大学生创新训练计划项目 · 太原理工大学 · 2026.05 – 2027.05

把泛知识短视频的"线性观看"变成"结构化留存"：用户在抖音/B站看视频时一键触发，系统自动完成 元数据解析 → 字幕/ASR 转写 → 大模型提炼，产出可编辑、可语义关联的结构化"知识胶囊"，并汇聚为个人 3D 知识图谱。

## 仓库结构

```
├── docs/                  # 开发启动文档（PRD / 技术设计 / 数据库 / API / 开发计划 / 测试计划）
├── backend/               # FastAPI 后端（解析、转写、LLM 提取、图谱）
├── android/               # Kotlin + Compose 客户端（分享接收、悬浮球、胶囊管理）
├── web/                   # Vue3 + Vant H5 管理端 + 3D 知识图谱
├── docker-compose.yml     # 本地基础设施（MySQL 等）
└── 大创申报材料（.docx/.doc，见根目录）
```

## 文档基线

| 文档 | 说明 |
| --- | --- |
| [docs/PRD.md](docs/PRD.md) | 需求基线：范围边界、功能清单与验收标准 |
| [docs/TECHNICAL_DESIGN.md](docs/TECHNICAL_DESIGN.md) | 技术选型、架构与开发规范 |
| [docs/DATABASE.md](docs/DATABASE.md) | 数据模型与表结构 |
| [docs/API.md](docs/API.md) | 接口契约 |
| [docs/DEVELOPMENT_PLAN.md](docs/DEVELOPMENT_PLAN.md) | 阶段计划与 WBS |
| [docs/TEST_PLAN.md](docs/TEST_PLAN.md) | 测试策略与用例 |

## 快速开始（阶段 0 完成后可用）

```bash
# 后端
cd backend
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# 数据库
docker compose up -d

# 前端 H5
cd web && npm install && npm run dev
```

## 团队与分工

| 成员 | 职能 |
| --- | --- |
| 刘郁鹏（负责人） | 统筹、产品设计、架构规划、Prompt 框架 |
| 待确认 | 前端开发与多模态交互（Android / Vue3） |
| 待确认 | 后端架构与网关调度（FastAPI / MySQL / Redis） |
| 待确认 | AI 解析与算法工程（LLM 接入 / ASR / Embedding） |

指导教师：张雄雄

## Android 真机联调

1. 手机与电脑连**同一 WiFi**；电脑后端跑在 `0.0.0.0:8000`（默认即是）；
2. 查电脑局域网 IP（`ipconfig`，如 `192.168.1.4`），App「设置」页填 `http://<该IP>:8000`；
3. 手机安装 APK：`android/app/build/outputs/apk/debug/app-debug.apk`；
4. 首次启动：授予「显示在其他应用上层」与通知权限 → 启动悬浮球；
5. 在抖音/B站点「分享 → 影海拾光」即可端到端提取（AC-01）。

注意事项：
- 本机系统代理会劫持 `localhost`，后端/前端/Ollama 一律用 `127.0.0.1` 直连；
- Ollama 不是系统服务，重启电脑后先运行 `ollama serve`；
- B 站对 yt-dlp 默认 UA 风控，已在后端内置浏览器 UA，不要改动。
