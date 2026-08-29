package com.yhsg.app.data

import com.yhsg.app.network.ApiClient
import com.yhsg.app.network.ExtractionCreate
import com.yhsg.app.network.TaskData
import kotlinx.coroutines.delay

/** 提取任务的提交与轮询封装，供分享接收/悬浮球共用（AC-01/02 时延埋点也挂在这）。 */
class ExtractRepository(private val prefs: Prefs) {

    sealed interface Outcome {
        data class Done(val taskId: String, val capsuleId: Long) : Outcome
        data class Failed(val reason: String) : Outcome
        /** 客户端停止等待，但服务端任务仍在跑，胶囊稍后会出现在列表（勿报"失败"）。 */
        data object StillProcessing : Outcome
    }

    /** 提交并轮询到终态；onStatus 用于 UI 展示中间态。 */
    suspend fun extractAndWait(
        shareText: String,
        onStatus: (suspend (String) -> Unit)? = null,
        pollIntervalMs: Long = 1500,
        // 长视频（40min+）服务端需 3 分钟以上；8 分钟留给极端情况，仍在
        // WorkManager 单任务 10 分钟上限内
        timeoutMs: Long = 480_000,
    ): Outcome {
        val api = ApiClient.service(prefs)
        onStatus?.invoke("提交中…")
        val created = try {
            api.createExtraction(ExtractionCreate(share_text = shareText))
        } catch (e: Exception) {
            return Outcome.Failed("网络错误：${e.message}")
        }
        if (created.code != 0) return Outcome.Failed(created.message)

        val taskId = created.data.task_id
        val deadline = System.currentTimeMillis() + timeoutMs
        while (System.currentTimeMillis() < deadline) {
            delay(pollIntervalMs)
            val env = try {
                api.getTask(taskId)
            } catch (e: Exception) {
                continue // 单次轮询失败不终止
            }
            when (env.data.status) {
                "done" -> {
                    onStatus?.invoke("完成")
                    return Outcome.Done(taskId, env.data.capsule_id ?: -1L)
                }
                "failed" -> return Outcome.Failed(env.data.stage_error ?: "提取失败")
                else -> onStatus?.invoke(statusLabel(env.data))
            }
        }
        return Outcome.StillProcessing
    }

    private fun statusLabel(t: TaskData) = when (t.status) {
        "resolving" -> "解析视频…"
        "transcribing" -> "提取视频内容…"
        "extracting" -> "AI 提炼知识胶囊…"
        else -> t.status
    }

    companion object {
        /** 从分享文本中提取 URL（与后端 resolver 的正则保持同构）。 */
        fun looksLikeShareText(text: String): Boolean =
            text.contains("b23.tv/") ||
                text.contains("bilibili.com/video/") ||
                text.contains("v.douyin.com/") ||
                text.contains("douyin.com/video/")
    }
}
