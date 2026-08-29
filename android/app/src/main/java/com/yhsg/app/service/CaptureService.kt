package com.yhsg.app.service

import android.app.Service
import android.content.Intent
import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioPlaybackCaptureConfiguration
import android.media.AudioRecord
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.IBinder
import com.yhsg.app.Notify
import com.yhsg.app.data.Prefs
import com.yhsg.app.network.ApiClient
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.ByteArrayOutputStream

/**
 * T3.7 音频捕获通道（TECHNICAL_DESIGN 关键设计 1-③）：
 * MediaProjection AudioPlaybackCapture 捕获正在播放的音频流，
 * 采集固定时长后编码 WAV 上传后端 → ASR 转写 → 胶囊，结果走通知。
 *
 * 限制：每次触发需系统授权弹窗（由 MainActivity 发起）；Android 10+ 可用。
 */
class CaptureService : Service() {

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        startForeground(2002, Notify.foreground(this))
        val resultCode = intent?.getIntExtra(EXTRA_RESULT_CODE, -1) ?: -1
        @Suppress("DEPRECATION")
        val data = intent?.getParcelableExtra(EXTRA_RESULT_DATA, Intent::class.java)
        if (resultCode == -1 || data == null) {
            stopSelf()
            return START_NOT_STICKY
        }

        val projection =
            (getSystemService(MEDIA_PROJECTION_SERVICE) as MediaProjectionManager)
                .getMediaProjection(resultCode, data)
        captureAndUpload(projection)
        return START_NOT_STICKY
    }

    private fun captureAndUpload(projection: MediaProjection) {
        CoroutineScope(Dispatchers.IO).launch {
            var failure: String? = null
            val wav = runCatching { recordWav(projection) }
                .onFailure { failure = it.message }
                .getOrNull()
            projection.stop()

            when {
                wav == null -> notify("捕获失败", failure ?: "未知错误")
                wav.size < 10_000 -> notify("没有捕获到声音", "确认目标 App 正在播放媒体音")
                else -> {
                    val task = upload(wav)
                    watch(task) // 轮询到终态，通知交付
                }
            }
            stopSelf()
        }
    }

    /** 采集 CAPTURE_SECONDS 秒系统混音，PCM 16bit/16k/mono → WAV 字节。 */
    private fun recordWav(projection: MediaProjection): ByteArray {
        val config = AudioPlaybackCaptureConfiguration.Builder(projection)
            .addMatchingUsage(AudioAttributes.USAGE_MEDIA)
            .build()
        val format = AudioFormat.Builder()
            .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
            .setSampleRate(16000)
            .setChannelMask(AudioFormat.CHANNEL_IN_MONO)
            .build()
        val minBuf = AudioRecord.getMinBufferSize(16000, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
        val recorder = AudioRecord.Builder()
            .setAudioFormat(format)
            .setBufferSizeInBytes(maxOf(minBuf, 16000)) // ≥1s
            .setAudioPlaybackCaptureConfig(config)
            .build()

        val pcm = ByteArrayOutputStream()
        val buf = ByteArray(16000) // 0.5s @16k16bit mono
        recorder.startRecording()
        try {
            val deadline = System.currentTimeMillis() + CAPTURE_SECONDS * 1000L
            while (System.currentTimeMillis() < deadline) {
                val n = recorder.read(buf, 0, buf.size)
                if (n > 0) pcm.write(buf, 0, n)
            }
        } finally {
            recorder.stop()
            recorder.release()
        }
        return wavBytes(pcm.toByteArray(), 16000, 1)
    }

    private fun wavBytes(pcm: ByteArray, sampleRate: Int, channels: Int): ByteArray {
        val bitsPerSample = 16
        val byteRate = sampleRate * channels * bitsPerSample / 8
        val out = ByteArrayOutputStream()
        fun le16(v: Int) { out.write(v and 0xFF); out.write((v shr 8) and 0xFF) }
        fun le32(v: Int) { le16(v and 0xFFFF); le16((v shr 16) and 0xFFFF) }
        out.write("RIFF".toByteArray()); le32(36 + pcm.size)
        out.write("WAVE".toByteArray())
        out.write("fmt ".toByteArray()); le32(16)
        le16(1); le16(channels); le32(sampleRate); le32(byteRate); le16(channels * 2); le16(bitsPerSample)
        out.write("data".toByteArray()); le32(pcm.size)
        out.write(pcm)
        return out.toByteArray()
    }

    private suspend fun upload(wav: ByteArray): Pair<String, Long> {
        val api = ApiClient.service(Prefs(this))
        val body = MultipartBody.Part.createFormData(
            "file", "capture.wav",
            wav.toRequestBody("audio/wav".toMediaType()),
        )
        val env = api.uploadAudio(body)
        if (env.code != 0) throw RuntimeException(env.message)
        return env.data.task_id to env.data.video_id
    }

    private suspend fun watch(task: Pair<String, Long>) {
        val (taskId, _) = task
        val api = ApiClient.service(Prefs(this))
        val deadline = System.currentTimeMillis() + 300_000
        while (System.currentTimeMillis() < deadline) {
            kotlinx.coroutines.delay(2000)
            val env = runCatching { api.getTask(taskId) }.getOrNull() ?: continue
            when (env.data.status) {
                "done" -> {
                    Notify.result(this, "捕获的声音已入光海", "点击查看知识胶囊", ok = true)
                    return
                }
                "failed" -> {
                    Notify.result(this, "捕获提取失败", env.data.stage_error ?: "未知原因", ok = false)
                    return
                }
            }
        }
        Notify.result(this, "仍在处理中", "稍后在 App 列表查看", ok = false)
    }

    private fun notify(title: String, text: String) = Notify.result(this, title, text, ok = false)

    override fun onDestroy() {
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    companion object {
        const val EXTRA_RESULT_CODE = "result_code"
        const val EXTRA_RESULT_DATA = "result_data"
        const val CAPTURE_SECONDS = 15
    }
}
