package com.yhsg.app.network

/** 统一响应 {code, message, data}，code=0 为成功（docs/API.md §1）。 */
data class ApiEnvelope<T>(val code: Int, val message: String, val data: T)

data class ExtractionCreate(
    val share_text: String? = null,
    val manual_text: String? = null,
    val title: String? = null,
)

data class TaskData(
    val task_id: String,
    val status: String,       // pending/resolving/transcribing/extracting/done/failed
    val video_id: Long,
    val capsule_id: Long? = null,
    val stage_error: String? = null,
)

data class CapsuleListData(val total: Int, val page: Int, val page_size: Int, val items: List<CapsuleSummary>)

data class CapsuleSummary(
    val id: Long,
    val theme: String,
    val category: String,
    val tags: List<String>,
    val steps_count: Int,
    val created_at: String,
)

data class CapsuleData(
    val id: Long,
    val theme: String,
    val category: String,
    val variables: List<String>,
    val steps: List<String>,
    val tags: List<String>,
    val video: VideoRef,
)

data class VideoRef(
    val id: Long,
    val platform: String,
    val title: String?,
    val source_url: String?,
)
