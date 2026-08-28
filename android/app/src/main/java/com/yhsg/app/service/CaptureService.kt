package com.yhsg.app.service

import android.app.Service
import android.content.Intent
import android.os.IBinder

/**
 * A7 音频捕获通道（M3，TECHNICAL_DESIGN 关键设计 1-③）：
 * MediaProjection AudioPlaybackCapture 捕获播放中的音频流 → 切片上传转写。
 * 限制：每次触发需系统授权弹窗；Android 14+ 必须以 mediaProjection 前台服务运行。
 */
class CaptureService : Service() {
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        // TODO(T3.7): 取 MediaProjection → AudioRecord(PLAYBACK_CAPTURE) → PCM 分片上传
        return START_NOT_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
