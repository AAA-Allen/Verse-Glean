package com.yhsg.app.network

import com.yhsg.app.data.Prefs
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

/**
 * 后端 API 客户端。服务器地址可在 App 设置页修改（真机联调指向开发机局域网 IP）。
 * 明文 HTTP 已在 Manifest 声明 usesCleartextTraffic（仅开发期）。
 *
 * 401 处理（review8 加固）：先用 refresh token 静默续期并重试一次；续期也失败才清登录态。
 */
object ApiClient {

    @Volatile
    private var currentBaseUrl: String? = null

    @Volatile
    private var cached: YingHaiApi? = null

    @Volatile
    private var cachedToken: String? = null

    private val refreshLock = Any()

    // 续期专用裸客户端：不带鉴权头、不经过本类拦截器，避免递归
    private val bareClient by lazy { OkHttpClient() }

    fun service(prefs: Prefs): YingHaiApi {
        val baseUrl = prefs.serverBaseUrl
        val token = prefs.apiToken
        val cachedApi = cached
        if (cachedApi != null && currentBaseUrl == baseUrl && cachedToken == token) return cachedApi

        synchronized(this) {
            val logging = HttpLoggingInterceptor().apply { level = HttpLoggingInterceptor.Level.BASIC }
            val client = OkHttpClient.Builder()
                .addInterceptor { chain ->
                    var resp = chain.proceed(
                        chain.request().newBuilder()
                            .header("Authorization", "Bearer $token")
                            .build()
                    )
                    if (resp.code == 401) {
                        val fresh = refresh(prefs, baseUrl)
                        if (fresh != null) {
                            resp.close()
                            resp = chain.proceed(
                                chain.request().newBuilder()
                                    .header("Authorization", "Bearer $fresh")
                                    .build()
                            )
                        }
                        if (resp.code == 401) prefs.logout()
                    }
                    resp
                }
                .addInterceptor(logging)
                .build()
            val api = Retrofit.Builder()
                .baseUrl("$baseUrl/")
                .client(client)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
                .create(YingHaiApi::class.java)
            currentBaseUrl = baseUrl
            cachedToken = token
            cached = api
            return api
        }
    }

    /** 用 refresh token 换新 access token；失败返回 null。加锁防止并发重复刷新。 */
    private fun refresh(prefs: Prefs, baseUrl: String): String? = synchronized(refreshLock) {
        val refreshToken = prefs.refreshToken
        if (refreshToken.isBlank()) return null
        val json = org.json.JSONObject().put("refresh_token", refreshToken).toString()
        try {
            bareClient.newCall(
                Request.Builder()
                    .url("$baseUrl/api/v1/auth/refresh")
                    .post(json.toRequestBody("application/json".toMediaType()))
                    .build()
            ).execute().use { resp ->
                if (!resp.isSuccessful) return null
                val root = org.json.JSONObject(resp.body?.string() ?: return null)
                if (root.optInt("code", -1) != 0) return null
                val data = root.getJSONObject("data")
                prefs.apiToken = data.getString("access_token")
                prefs.refreshToken = data.getString("refresh_token")
                data.getString("access_token")
            }
        } catch (_: Exception) {
            null
        }
    }
}
