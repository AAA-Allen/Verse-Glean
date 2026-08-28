package com.yhsg.app

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import com.yhsg.app.network.ApiClient
import com.yhsg.app.network.ExtractionCreate
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

/**
 * A1 主采集通道（TECHNICAL_DESIGN 关键设计 1-①）：
 * 用户在抖音/B站点「分享 → 影海拾光」，这里取 EXTRA_TEXT 提交提取，跳转等待页。
 */
class ShareReceiverActivity : Activity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val shareText = intent?.getStringExtra(Intent.EXTRA_TEXT)
        if (shareText.isNullOrBlank()) {
            Toast.makeText(this, "未收到分享内容", Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        // TODO(T2.2): 换成 Compose 等待页（轮询 task 进度 + 结果卡片），当前骨架仅提交
        CoroutineScope(Dispatchers.IO).launch {
            runCatching { ApiClient.service.createExtraction(ExtractionCreate(share_text = shareText)) }
                .onSuccess { env ->
                    if (env.code == 0) {
                        Toast.makeText(this@ShareReceiverActivity, "已提交提取", Toast.LENGTH_SHORT).show()
                    } else {
                        Toast.makeText(this@ShareReceiverActivity, env.message, Toast.LENGTH_LONG).show()
                    }
                }
                .onFailure {
                    Toast.makeText(this@ShareReceiverActivity, "网络错误：${it.message}", Toast.LENGTH_LONG).show()
                }
            finish()
        }
    }
}
