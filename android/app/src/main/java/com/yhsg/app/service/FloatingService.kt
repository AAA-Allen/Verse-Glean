package com.yhsg.app.service

import android.annotation.SuppressLint
import android.app.Service
import android.content.ClipboardManager
import android.content.Intent
import android.graphics.PixelFormat
import android.os.IBinder
import android.view.Gravity
import android.view.MotionEvent
import android.view.WindowManager
import android.widget.TextView

/**
 * A2 悬浮球服务（TECHNICAL_DESIGN §4.5）：
 * - 收起态：不可聚焦小球，拖拽 + 边缘吸附 + 位置记忆，不抢原 App 焦点；
 * - 展开态：FLAG_FOCUSABLE 可聚焦卡片 → 有焦点才可读剪贴板（Android 10+ 限制）。
 */
class FloatingService : Service() {

    private lateinit var wm: WindowManager
    private var ballView: TextView? = null
    private var expanded = false

    @SuppressLint("ClickableViewAccessibility")
    override fun onCreate() {
        super.onCreate()
        wm = getSystemService(WINDOW_SERVICE) as WindowManager
        ballView = TextView(this).apply {
            text = "拾"
            textSize = 18f
            gravity = android.view.Gravity.CENTER
            setOnClickListener { toggleExpand() }
        }
        // TODO(T2.3): 换 ComposeView/自绘气泡 + 拖拽手势 + 边缘吸附 + SharedPreferences 位置记忆
        wm.addView(
            ballView,
            WindowManager.LayoutParams(
                WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE, // 收起态不抢焦点
                PixelFormat.TRANSLUCENT,
            ).apply { gravity = Gravity.TOP or Gravity.START; x = 40; y = 200 },
        )
    }

    private fun toggleExpand() {
        expanded = !expanded
        if (expanded) {
            val clip = getSystemService(ClipboardManager::class.java)?.primaryClip
            val text = clip?.getItemAt(0)?.text?.toString().orEmpty()
            // TODO(T2.4): 有效口令正则校验 → 提交 API → 结果卡片 3s 自动收起；
            //  无口令时展示引导文案 strings/floating_hint
        }
    }

    private fun onTouch(v: android.view.View, e: MotionEvent): Boolean = false

    override fun onDestroy() {
        ballView?.let { wm.removeView(it) }
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
