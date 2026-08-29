package com.yhsg.app.service

import android.annotation.SuppressLint
import android.app.Service
import android.content.ClipboardManager
import android.content.Intent
import android.graphics.Color
import android.graphics.PixelFormat
import android.graphics.drawable.GradientDrawable
import android.os.IBinder
import android.util.TypedValue
import android.view.Gravity
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import android.widget.LinearLayout
import android.widget.TextView
import com.yhsg.app.Notify
import com.yhsg.app.data.ExtractRepository
import com.yhsg.app.data.Prefs
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlin.math.abs

/**
 * A2 悬浮球（TECHNICAL_DESIGN §4.5）：
 * - 收起态：不可聚焦小球，拖拽 + 边缘吸附 + 位置记忆，不抢原 App 焦点；
 * - 展开态：切换 FLAG_FOCUSABLE 获得窗口焦点后才可读剪贴板（Android 10+ 限制），
 *   有效口令自动提交，无效则展示引导；完成后自动收回。
 */
class FloatingService : Service() {

    private lateinit var wm: WindowManager
    private lateinit var prefs: Prefs
    private lateinit var ball: TextView
    private lateinit var card: LinearLayout
    private lateinit var cardText: TextView

    private var expanded = false
    private var busy = false
    private var downX = 0f
    private var downY = 0f
    private var dragging = false

    private val ballParams by lazy {
        WindowManager.LayoutParams(
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE, // 收起态不抢原 App 焦点
            PixelFormat.TRANSLUCENT,
        ).apply {
            gravity = Gravity.TOP or Gravity.START
            x = prefs.ballX
            y = prefs.ballY
        }
    }

    override fun onCreate() {
        super.onCreate()
        // specialUse 前台服务：Android 12+ 必须限时调 startForeground，否则系统崩溃
        startForeground(2001, Notify.foreground(this))
        prefs = Prefs(this)
        wm = getSystemService(WINDOW_SERVICE) as WindowManager
        wm.addView(createBall(), ballParams)
    }

    @SuppressLint("ClickableViewAccessibility")
    private fun createBall(): View {
        val size = dp(52)
        ball = TextView(this).apply {
            text = "拾"
            textSize = 20f
            gravity = Gravity.CENTER
            setTextColor(Color.WHITE)
            background = GradientDrawable().apply {
                shape = GradientDrawable.OVAL
                setColor(Color.parseColor("#CC4F8EF7"))
            }
        }
        ball.layoutParams = android.view.ViewGroup.LayoutParams(size, size)

        card = createCard()
        ball.setOnTouchListener { _, e ->
            when (e.action) {
                MotionEvent.ACTION_DOWN -> {
                    downX = e.rawX; downY = e.rawY; dragging = false
                    true
                }
                MotionEvent.ACTION_MOVE -> {
                    val dx = e.rawX - downX
                    val dy = e.rawY - downY
                    if (dragging || abs(dx) > dp(6) || abs(dy) > dp(6)) {
                        dragging = true
                        ballParams.x = (ballParams.x + dx).toInt().coerceAtLeast(0)
                        ballParams.y = (ballParams.y + dy).toInt().coerceAtLeast(0)
                        wm.updateViewLayout(ball, ballParams)
                        downX = e.rawX; downY = e.rawY
                    }
                    true
                }
                MotionEvent.ACTION_UP -> {
                    if (dragging) snapToEdgeAndRemember() else toggleExpand()
                    true
                }
                else -> false
            }
        }
        return ball
    }

    private fun createCard(): LinearLayout {
        cardText = TextView(this).apply {
            textSize = 14f
            setTextColor(Color.WHITE)
            setPadding(dp(16), dp(12), dp(16), dp(12))
            text = hint
        }
        return LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            background = GradientDrawable().apply {
                cornerRadius = dp(14).toFloat()
                setColor(Color.parseColor("#E6202030"))
            }
            addView(cardText)
        }
    }

    private val hint: String
        get() = "先在视频 App 点「分享 → 复制链接」，再点我"

    /** 收起 ⇄ 展开：展开时必须切换为可聚焦窗口，才有资格读剪贴板（Android 10+）。 */
    private fun toggleExpand() {
        if (busy) return
        expanded = !expanded
        if (expanded) {
            // flags=0 即默认可聚焦窗口（无 FLAG_NOT_FOCUSABLE），聚焦才能读剪贴板
            wm.addView(card, WindowManager.LayoutParams(
                WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                0,
                PixelFormat.TRANSLUCENT,
            ).apply { gravity = Gravity.CENTER })
            wm.removeView(ball)

            val clip = getSystemService(ClipboardManager::class.java)
                ?.primaryClip?.getItemAt(0)?.text?.toString().orEmpty()
            cardText.text = if (ExtractRepository.looksLikeShareText(clip)) {
                busy = true
                submitAndWatch(clip)
                "已识别链接，提取中…"
            } else {
                // 无有效口令：展示引导，2.5s 自动收回（US-4）
                cardText.postDelayed(Runnable { if (expanded) toggleExpand() }, 2500)
                hint
            }
        } else {
            wm.removeView(card)
            wm.addView(ball, ballParams)
        }
    }

    private fun submitAndWatch(shareText: String) {
        CoroutineScope(Dispatchers.IO).launch {
            val outcome = ExtractRepository(prefs).extractAndWait(
                shareText,
                onStatus = { s: String ->
                    withContext(Dispatchers.Main) { cardText.text = s }
                },
            )
            withContext(Dispatchers.Main) {
                busy = false
                when (outcome) {
                    is ExtractRepository.Outcome.Done -> {
                        cardText.text = "✓ 已入光海"
                        Notify.result(this@FloatingService, "知识胶囊已入光海", "点击查看详情", ok = true)
                        cardText.postDelayed(Runnable { if (expanded) toggleExpand() }, 1500)
                    }
                    is ExtractRepository.Outcome.Failed -> {
                        cardText.text = "提取失败：${outcome.reason.take(80)}"
                        Notify.result(this@FloatingService, "提取失败", outcome.reason, ok = false)
                        cardText.postDelayed(Runnable { if (expanded) toggleExpand() }, 3000)
                    }
                }
            }
        }
    }

    /** 边缘吸附：距哪边近吸哪边，并保存位置（AC-02 位置记忆）。 */
    private fun snapToEdgeAndRemember() {
        val screenW = resources.displayMetrics.widthPixels
        val maxX = screenW - dp(52)
        ballParams.x = if (ballParams.x < maxX / 2) dp(8) else maxX - dp(8)
        wm.updateViewLayout(ball, ballParams)
        prefs.ballX = ballParams.x
        prefs.ballY = ballParams.y
    }

    private fun dp(v: Int): Int = TypedValue.applyDimension(
        TypedValue.COMPLEX_UNIT_DIP, v.toFloat(), resources.displayMetrics
    ).toInt()

    override fun onDestroy() {
        runCatching { if (expanded) wm.removeView(card) else wm.removeView(ball) }
        super.onDestroy()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int = START_STICKY

    override fun onBind(intent: Intent?): IBinder? = null
}
