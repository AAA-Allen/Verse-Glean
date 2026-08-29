package com.yhsg.app

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import androidx.core.app.NotificationCompat

/** 通知：提取结果通知（T2.5）+ 悬浮球前台服务常驻通知。 */
object Notify {
    private const val CHANNEL_RESULT = "extract_result"
    private const val CHANNEL_FLOATING = "floating_service"

    fun ensureChannel(context: Context) {
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        manager.createNotificationChannel(
            NotificationChannel(CHANNEL_RESULT, "提取结果", NotificationManager.IMPORTANCE_DEFAULT)
        )
        // 悬浮球前台服务的常驻通知：低优先级、无声，仅满足系统前台服务要求
        manager.createNotificationChannel(
            NotificationChannel(CHANNEL_FLOATING, "悬浮球服务", NotificationManager.IMPORTANCE_MIN)
        )
    }

    fun foreground(context: Context): android.app.Notification {
        ensureChannel(context)
        return NotificationCompat.Builder(context, CHANNEL_FLOATING)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle("影海拾光悬浮球运行中")
            .setPriority(NotificationCompat.PRIORITY_MIN)
            .setShowWhen(false)
            .build()
    }

    fun result(context: Context, title: String, text: String, ok: Boolean) {
        ensureChannel(context)
        val intent = PendingIntent.getActivity(
            context, 0,
            Intent(context, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )
        val notification = NotificationCompat.Builder(context, CHANNEL_RESULT)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle(title)
            .setContentText(text)
            .setAutoCancel(true)
            .setContentIntent(intent)
            .build()
        val id = if (ok) 1001 else 1002
        androidx.core.app.NotificationManagerCompat.from(context).notify(id, notification)
    }
}
