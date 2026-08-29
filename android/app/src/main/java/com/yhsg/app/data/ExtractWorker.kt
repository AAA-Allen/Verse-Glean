package com.yhsg.app.data

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import androidx.work.workDataOf
import com.yhsg.app.Notify

/**
 * 后台提取任务（用户反馈"等待期间不能干其他事"后引入）：
 * 分享接收只负责入队并立即退出，轮询在 WorkManager 中进行——
 * 用户可继续刷视频，完成后以通知交付；进程被杀任务也不丢。
 */
class ExtractWorker(context: Context, params: WorkerParameters) :
    CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        val shareText = inputData.getString(KEY_SHARE_TEXT) ?: return Result.failure()
        val startedAt = System.currentTimeMillis()
        return when (val outcome = ExtractRepository(Prefs(applicationContext)).extractAndWait(shareText)) {
            is ExtractRepository.Outcome.Done -> {
                val secs = (System.currentTimeMillis() - startedAt) / 1000.0
                Notify.result(
                    applicationContext,
                    "知识胶囊已入光海",
                    "耗时 ${secs}s，点击查看详情",
                    ok = true,
                )
                Result.success()
            }
            is ExtractRepository.Outcome.Failed -> {
                Notify.result(applicationContext, "提取失败", outcome.reason, ok = false)
                Result.success() // 业务失败也是"任务完成"，无需系统重试
            }
            is ExtractRepository.Outcome.StillProcessing -> {
                // 长视频超出客户端等待窗口：服务端仍在跑，勿谎报失败
                Notify.result(
                    applicationContext,
                    "仍在处理中",
                    "这条视频内容较长，稍后打开 App 在列表查看结果",
                    ok = false,
                )
                Result.success()
            }
        }
    }

    companion object {
        const val KEY_SHARE_TEXT = "share_text"

        fun inputData(shareText: String) = workDataOf(KEY_SHARE_TEXT to shareText)
    }
}
