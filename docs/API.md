# API.md — 接口文档

## 文档信息

| 项 | 内容 |
| --- | --- |
| 项目名 | 影海拾光——视频平台知识胶囊提取系统 |
| 文档版本 | v0.1 |
| 创建时间 | 2026-08-28 |
| 负责人 | 刘郁鹏 |
| 状态 | 草稿 |

> 上游输入：DATABASE.md 表结构（capsules/extraction_tasks 字段）与 PRD 功能清单（B1–B9、A1–A7、C1–C3）。接口实现与本文档不一致视为缺陷；API 变更必须同步更新本文档。

---

## 1. 接口通用约定

- 基础路径：`/api/v1`；协议 HTTP（内网/校园）或 HTTPS（上线）；数据格式 JSON（UTF-8）
- 鉴权：请求头 `Authorization: Bearer <token>`；M1 为单用户固定 token（服务端配置），M3 起 JWT（access 2h）
- 通用响应结构：

```json
{ "code": 0, "message": "ok", "data": {} }
```

- 分页通用参数：`page`（≥1，默认 1）、`page_size`（1–50，默认 20）；分页响应 `data.items` + `data.total` + `data.page` + `data.page_size`
- 时间格式：ISO 8601，如 `2026-08-28T12:00:00+08:00`
- 幂等：`POST /extractions` 对同一用户同一 source_url 的进行中任务直接返回该 task（不重复建任务）

## 2. 通用错误码表

| code | message 示例 | http_status | 说明 | 处理建议 |
| --- | --- | --- | --- | --- |
| 0 | ok | 200 | 成功 | — |
| 1001 | invalid parameter: share_text | 422 | 参数校验失败 | 按 detail 修正入参 |
| 1002 | unauthorized | 401 | 未携带/无效 token | 重新登录或检查 token |
| 1004 | resource not found | 404 | 资源不存在或已软删 | 刷新列表 |
| 2001 | share text unresolvable | 422 | 分享口令无法解析出视频 | 引导用户走手动粘贴通道 |
| 2002 | transcript unavailable | 422 | 字幕与 ASR 均失败 | 用户手动粘贴文案重试 |
| 2003 | extraction failed | 502 | LLM 提取重试后仍失败 | 可重试；持续失败上报 |
| 2004 | task not found | 404 | task_id 不存在 | 检查 task_id |
| 3001 | rate limited | 429 | 触发限流 | 退避重试 |
| 5000 | internal error | 500 | 服务端异常 | 上报日志 |

## 3. 接口清单

### 3.1 提取任务

#### 3.1.1 提交提取任务（分享文本 / 手动文案）

`POST /api/v1/extractions` — 对应 PRD A1/A2/B1/B5

请求：

```json
{
  "share_text": "【抖音】复制的分享口令，含 https://v.douyin.com/xxxx/",
  "manual_text": null,
  "title": null
}
```

| 参数 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| share_text | body | string | 二选一 | 分享口令/链接文本，≤2000 字 |
| manual_text | body | string | 二选一 | 手动粘贴的视频文案，≤5000 字；与 share_text 互斥 |
| title | body | string | 否 | manual_text 模式下的补充标题 |

响应（成功）：

```json
{
  "code": 0, "message": "ok",
  "data": {
    "task_id": "20260828120000_000042",
    "status": "pending",
    "video_id": 17
  }
}
```

错误：`1001`（两者都传/都为空/超长）、`1002`、`3001`。

#### 3.1.2 查询任务进度

`GET /api/v1/extractions/{task_id}` — 对应 PRD B6/A3

响应（进行中）：

```json
{
  "code": 0, "message": "ok",
  "data": {
    "task_id": "20260828120000_000042",
    "status": "transcribing",
    "stage_error": null,
    "capsule_id": null,
    "created_at": "2026-08-28T12:00:00+08:00",
    "updated_at": "2026-08-28T12:00:08+08:00"
  }
}
```

响应（成功）：

```json
{
  "code": 0, "message": "ok",
  "data": {
    "task_id": "20260828120000_000042",
    "status": "done",
    "stage_error": null,
    "capsule_id": 33,
    "created_at": "2026-08-28T12:00:00+08:00",
    "updated_at": "2026-08-28T12:00:12+08:00"
  }
}
```

错误：`1002`（他人任务同样返回 404，防越权探测）、`2004`。

轮询建议：App/H5 每 2s 一次，`done`/`failed` 终止；`failed` 时按 `stage_error` 展示原因（US-2/US-3）。

#### 3.1.3 失败任务手动文案重试

`POST /api/v1/extractions/{task_id}/manual-text` — 对应状态机 `failed → transcribing`、PRD B5

```json
{ "manual_text": "在B站简介里复制的文案…" }
```

响应同 3.1.1（原 task 状态重置为 transcribing）。错误：`1001`、`2004`；仅 `failed` 状态任务可调用。

### 3.2 知识胶囊

#### 3.2.1 胶囊列表

`GET /api/v1/capsules?page=1&page_size=20&tag=excel&keyword=函数` — 对应 PRD A4/C2

| 参数 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| page / page_size | query | int | 否 | 通用分页 |
| tag | query | string | 否 | 标签精确匹配（走 capsule_tags） |
| keyword | query | string | 否 | theme 模糊匹配 |
| category | query | string | 否 | `step`/`config`/`theory` |

响应：

```json
{
  "code": 0, "message": "ok",
  "data": {
    "total": 42, "page": 1, "page_size": 20,
    "items": [
      {
        "id": 33,
        "theme": "Excel VLOOKUP 多表匹配",
        "category": "step",
        "tags": ["excel", "函数"],
        "steps_count": 5,
        "video": { "id": 17, "platform": "bilibili", "title": "10分钟学会VLOOKUP", "source_url": "https://b23.tv/xxx" },
        "created_at": "2026-08-28T12:00:12+08:00"
      }
    ]
  }
}
```

#### 3.2.2 胶囊详情

`GET /api/v1/capsules/{id}` — 对应 PRD A4/C3 下钻

```json
{
  "code": 0, "message": "ok",
  "data": {
    "id": 33,
    "theme": "Excel VLOOKUP 多表匹配",
    "category": "step",
    "variables": ["查找值", "数据表区域", "列序号"],
    "steps": ["选中目标单元格…", "输入 =VLOOKUP(查找值,区域,列序号,0)…"],
    "tags": ["excel", "函数"],
    "prompt_version": "step-v3",
    "model": "qwen-plus",
    "transcript_source": "subtitle_api",
    "video": { "id": 17, "platform": "bilibili", "title": "10分钟学会VLOOKUP", "source_url": "https://b23.tv/xxx", "cover_url": "https://i0.hdslb.com/xxx.jpg", "duration_sec": 612 },
    "created_at": "2026-08-28T12:00:12+08:00",
    "updated_at": "2026-08-28T12:00:12+08:00"
  }
}
```

#### 3.2.3 编辑胶囊

`PATCH /api/v1/capsules/{id}` — 对应 PRD A5/C2

```json
{ "theme": "Excel VLOOKUP 精确匹配", "steps": ["…"], "tags": ["excel"] }
```

可编辑字段：`theme`、`variables`、`steps`、`tags`、`category`。编辑 `tags` 时同步重写 capsule_tags；编辑后失效该用户图谱缓存。响应：更新后的完整胶囊（同 3.2.2）。错误：`1001`、`1004`。

#### 3.2.4 删除胶囊（软删）

`DELETE /api/v1/capsules/{id}` — 对应 AC-06

响应：`{ "code": 0, "message": "ok", "data": { "id": 33 } }`；同时清理 embeddings 与相邻 capsule_links。

### 3.3 知识图谱

#### 3.3.1 图谱数据

`GET /api/v1/graph?category=&tag=` — 对应 PRD B8/C3

```json
{
  "code": 0, "message": "ok",
  "data": {
    "nodes": [
      { "id": 33, "theme": "Excel VLOOKUP 多表匹配", "category": "step", "tags": ["excel"], "degree": 4 }
    ],
    "edges": [
      { "source": 33, "target": 21, "similarity": 0.81 }
    ]
  }
}
```

说明：仅返回未软删胶囊；孤立节点（degree=0）默认包含（前端可过滤）。

### 3.4 认证（M3 起启用）

#### 3.4.1 登录

`POST /api/v1/auth/login`

```json
{ "username": "liuyupeng", "password": "******" }
```

```json
{
  "code": 0, "message": "ok",
  "data": { "access_token": "eyJ…", "refresh_token": "eyJ…", "expires_in": 7200, "user": { "id": 1, "nickname": "刘郁鹏" } }
}
```

错误：`1002`（凭据错误）、`3001`（连续失败限流）。

## 4. 鉴权与安全约束

- 除 `POST /auth/login` 外全部接口需鉴权；资源级校验：查询/修改均限定 `user_id = 当前用户`，越权一律 404
- 限流：`POST /extractions` 单用户 10 次/分钟、全服 60 次/分钟（M1 内存计数，M4 迁 Redis）；`POST /auth/login` 单 IP 5 次/分钟
- 敏感信息：响应永不返回 SESSDATA、API Key、LLM 原始输出（raw_llm_output 仅服务端留存）
- 防重放：M3 上线后 login 接口加时间戳+nonce；内网 MVP 期依赖 HTTPS + token 即可

---

> 遗留待确认项：① 是否需要 `POST /capsules/{id}/reextract`（同视频重新提取）接口；② 图谱接口是否支持增量（客户端 WebSocket 推送，当前轮询即可）。
