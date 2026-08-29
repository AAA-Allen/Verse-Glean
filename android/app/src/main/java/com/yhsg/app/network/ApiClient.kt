package com.yhsg.app.network

import com.yhsg.app.data.Prefs
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

/**
 * 后端 API 客户端。服务器地址可在 App 设置页修改（真机联调指向开发机局域网 IP）。
 * 明文 HTTP 已在 Manifest 声明 usesCleartextTraffic（仅开发期）。
 */
object ApiClient {

    @Volatile
    private var currentBaseUrl: String? = null

    @Volatile
    private var cached: YingHaiApi? = null

    fun service(prefs: Prefs): YingHaiApi {
        val baseUrl = prefs.serverBaseUrl
        val token = prefs.apiToken
        val cachedApi = cached
        if (cachedApi != null && currentBaseUrl == baseUrl && cachedToken == token) return cachedApi

        synchronized(this) {
            val logging = HttpLoggingInterceptor().apply { level = HttpLoggingInterceptor.Level.BASIC }
            val client = OkHttpClient.Builder()
                .addInterceptor { chain ->
                    chain.proceed(
                        chain.request().newBuilder()
                            .header("Authorization", "Bearer $token")
                            .build()
                    )
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

    @Volatile
    private var cachedToken: String? = null
}
