# 按 project-dev-kickoff 流水线生成《影海拾光》开发启动文档（含阶段计划）

## 输出
`D:\浮光收集指南\docs\` 下 6 份文档，按模板与依赖顺序生成，未定项标`待确认`：PRD → TECHNICAL_DESIGN → DATABASE → API → DEVELOPMENT_PLAN → TEST_PLAN。

## 各文档要点
1. **PRD.md** — 成功指标（提取成功率/JSON合法率≥90%、悬浮唤醒<500ms、端到端≤30s）、A（Android采集）/B（后端）/C（H5+图谱）三模块功能清单含验收标准、异常流用户故事、Mermaid 业务流程与任务状态机、AC-01~10 验收总表
2. **TECHNICAL_DESIGN.md** — 选型理由与备选对比、三层架构图、提取链时序与降级回退、关键模块（resolver / transcript 三级降级 / extractor Prompt 引擎 / graph / Android 分享接收+悬浮球）、难点取舍（Android 10+ 剪贴板限制、抖音风控、3d-force-graph）、目录结构、开发规范（命名/分层/Git/依赖/质量门槛）
3. **DATABASE.md** — ER 图；users / videos / extraction_tasks / capsules / capsule_tags / embeddings / capsule_links 字段级表格、索引依据、软删与幂等去重、Alembic 迁移
4. **API.md** — `/api/v1` 约定、统一响应与错误码表、extraction 任务提交/查询、capsules CRUD、graph、auth 接口（含示例）
5. **DEVELOPMENT_PLAN.md** — 阶段计划双层结构：
   - 近期执行：阶段0 开发准备（第0周）→ 阶段1 后端闭环（第1–2周）→ 阶段2 Android MVP（第3–5周）→ 阶段3 H5+图谱+音频通道（第6–9周）→ 阶段4 评测打磨（第10周起），每阶段含目标/交付物/完成标准
   - 对齐申报书 12 个月四阶段（结题口径）；WBS 拆到任务粒度（负责人/依赖/工时/状态）、关键路径、协作规范、风险表
6. **TEST_PLAN.md** — 分层测试策略、用例与 AC 编号映射、5垂类×200条 Prompt 评测集、性能与真机端到端、通过标准与缺陷管理

## 收尾
四项交叉核对（TEST↔PRD、API↔DATABASE、PLAN↔模块、规范落地），输出文档清单+状态+遗留待确认项汇总。文档定稿后即按阶段 0 启动开发。