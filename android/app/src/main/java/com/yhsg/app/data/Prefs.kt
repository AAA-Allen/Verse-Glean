package com.yhsg.app.data

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import com.yhsg.app.BuildConfig

/** 轻量本地配置：服务器地址、悬浮球位置、登录态。token 存加密 prefs（review8 加固）。 */
class Prefs(context: Context) {
    private val sp: SharedPreferences =
        context.getSharedPreferences("yhsg", Context.MODE_PRIVATE)

    // JWT 等敏感项单独存加密文件；升级前明文存的 token 首次读取时迁移进来
    private val secure: SharedPreferences = EncryptedSharedPreferences.create(
        context,
        "yhsg_secure",
        MasterKey.Builder(context).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build(),
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
    )

    var serverBaseUrl: String
        get() = sp.getString(KEY_SERVER, DEFAULT_SERVER) ?: DEFAULT_SERVER
        set(v) = sp.edit().putString(KEY_SERVER, v.trimEnd('/')).apply()

    var apiToken: String
        get() = secure.getString(KEY_TOKEN, null) ?: migrateLegacyToken() ?: FALLBACK_TOKEN
        set(v) = secure.edit().putString(KEY_TOKEN, v).apply()

    var refreshToken: String
        get() = secure.getString(KEY_REFRESH, "") ?: ""
        set(v) = secure.edit().putString(KEY_REFRESH, v).apply()

    var nickname: String
        get() = sp.getString(KEY_NICKNAME, "") ?: ""
        set(v) = sp.edit().putString(KEY_NICKNAME, v).apply()

    var ballX: Int
        get() = sp.getInt(KEY_BALL_X, 40)
        set(v) = sp.edit().putInt(KEY_BALL_X, v).apply()

    var ballY: Int
        get() = sp.getInt(KEY_BALL_Y, 200)
        set(v) = sp.edit().putInt(KEY_BALL_Y, v).apply()

    /** 是否已通过 JWT 登录（debug 构建的 M1 兜底 token 不算）。 */
    val isLoggedIn: Boolean
        get() = secure.contains(KEY_TOKEN) || sp.contains(KEY_TOKEN)

    fun logout() {
        secure.edit().remove(KEY_TOKEN).remove(KEY_REFRESH).apply()
        // 清掉旧版本可能残留的明文 token
        sp.edit().remove(KEY_TOKEN).apply()
    }

    private fun migrateLegacyToken(): String? {
        val legacy = sp.getString(KEY_TOKEN, null) ?: return null
        secure.edit().putString(KEY_TOKEN, legacy).apply()
        sp.edit().remove(KEY_TOKEN).apply()
        return legacy
    }

    companion object {
        // 占位默认值：克隆后必须在 App「设置」页改成开发机的局域网地址（第七轮审查 2.4）
        const val DEFAULT_SERVER = "http://192.168.1.100:8000"
        private const val KEY_SERVER = "server_base_url"
        private const val KEY_TOKEN = "api_token"
        private const val KEY_REFRESH = "refresh_token"
        private const val KEY_NICKNAME = "nickname"
        private const val KEY_BALL_X = "ball_x"
        private const val KEY_BALL_Y = "ball_y"

        // debug 构建保留 M1 单用户固定 token 兜底（联调免登录）；release 必须走 JWT 登录
        private val FALLBACK_TOKEN = if (BuildConfig.DEBUG) "dev-single-user-token" else ""
    }
}
