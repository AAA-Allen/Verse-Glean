package com.yhsg.app

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.view.Gravity
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import com.yhsg.app.data.ExtractRepository
import com.yhsg.app.data.Prefs
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * A1 主采集通道（TECHNICAL_DESIGN 关键设计 1-①）：
 * 用户在抖音/B站点「分享 → 影海拾光」，这里取 EXTRA_TEXT 提交提取，展示进度后通知结果。
 */
class ShareReceiverActivity : Activity() {

    private lateinit var prefs: Prefs
    private lateinit var statusView: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        prefs = Prefs(this)
        statusView = TextView(this).apply {
            textSize = 16f
            gravity = Gravity.CENTER
            setPadding(48, 48, 48, 48)
        }
        setContentView(
            LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                gravity = Gravity.CENTER
                addView(statusView)
            }
        )

        val shareText = intent?.getStringExtra(Intent.EXTRA_TEXT)
        if (shareText.isNullOrBlank()) {
            toast("未收到分享内容")
            finish()
            return
        }
        if (!ExtractRepository.looksLikeShareText(shareText)) {
            toast("未识别到视频链接，可长按悬浮球手动粘贴文案")
            finish()
            return
        }

        statusView.text = "已接收，开始提取…"
        val startedAt = System.currentTimeMillis()
        CoroutineScope(Dispatchers.IO).launch {
            val outcome = ExtractRepository(prefs).extractAndWait(
                shareText,
                onStatus = { s: String ->
                    withContext(Dispatchers.Main) { statusView.text = s }
                },
            )
            val elapsed = (System.currentTimeMillis() - startedAt) / 1000.0
            withContext(Dispatchers.Main) {
                when (outcome) {
                    is ExtractRepository.Outcome.Done -> {
                        Notify.result(this@ShareReceiverActivity, "知识胶囊已入光海", "耗时 ${elapsed}s，点击查看", ok = true)
                        finish()
                    }
                    is ExtractRepository.Outcome.Failed -> {
                        statusView.text = "提取失败：${outcome.reason}\n\n可回主界面手动粘贴文案重试"
                        Notify.result(this@ShareReceiverActivity, "提取失败", outcome.reason, ok = false)
                        // 留 3s 让用户看到原因再关闭
                        statusView.postDelayed(Runnable { finish() }, 3000)
                    }
                }
            }
        }
    }

    private fun toast(msg: String) =
        Toast.makeText(this, msg, Toast.LENGTH_LONG).show()
}
