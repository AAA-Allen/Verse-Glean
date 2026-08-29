package com.yhsg.app.data

import android.content.Context
import android.content.SharedPreferences

/** 轻量本地配置：服务器地址、悬浮球位置、token。 */
class Prefs(context: Context) {
    private val sp: SharedPreferences =
        context.getSharedPreferences("yhsg", Context.MODE_PRIVATE)

    var serverBaseUrl: String
        get() = sp.getString(KEY_SERVER, DEFAULT_SERVER) ?: DEFAULT_SERVER
        set(v) = sp.edit().putString(KEY_SERVER, v.trimEnd('/')).apply()

    var apiToken: String
        get() = sp.getString(KEY_TOKEN, "dev-single-user-token") ?: "dev-single-user-token"
        set(v) = sp.edit().putString(KEY_TOKEN, v).apply()

    var ballX: Int
        get() = sp.getInt(KEY_BALL_X, 40)
        set(v) = sp.edit().putInt(KEY_BALL_X, v).apply()

    var ballY: Int
        get() = sp.getInt(KEY_BALL_Y, 200)
        set(v) = sp.edit().putInt(KEY_BALL_Y, v).apply()

    companion object {
        // 默认指向开发机局域网地址（真机与电脑需同一 WiFi；在 App 设置页可改）
        const val DEFAULT_SERVER = "http://192.168.1.4:8000"
        private const val KEY_SERVER = "server_base_url"
        private const val KEY_TOKEN = "api_token"
        private const val KEY_BALL_X = "ball_x"
        private const val KEY_BALL_Y = "ball_y"
    }
}
