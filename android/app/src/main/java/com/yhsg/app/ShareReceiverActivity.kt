package com.yhsg.app

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import com.yhsg.app.data.ExtractRepository
import com.yhsg.app.data.ExtractWorker

/**
 * A1 主采集通道（TECHNICAL_DESIGN 关键设计 1-①）：
 * 用户在抖音/B站点「分享 → 影海拾光」——校验链接后入队 WorkManager 立即退出，
 * 不阻塞用户操作；完成/失败通过通知交付（用户反馈"等待期间不能干其他事"后重构）。
 */
class ShareReceiverActivity : Activity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val shareText = intent?.getStringExtra(Intent.EXTRA_TEXT)
        if (shareText.isNullOrBlank()) {
            toast("未收到分享内容")
            finish()
            return
        }
        if (!ExtractRepository.looksLikeShareText(shareText)) {
            toast("未识别到视频链接，可打开 App 手动粘贴文案")
            finish()
            return
        }

        WorkManager.getInstance(this).enqueue(
            OneTimeWorkRequestBuilder<ExtractWorker>()
                .setInputData(ExtractWorker.inputData(shareText))
                .build()
        )
        toast("已开始提取，完成后会通知你 ✓ 可继续刷视频")
        finish()
    }

    private fun toast(msg: String) =
        Toast.makeText(this, msg, Toast.LENGTH_LONG).show()
}
