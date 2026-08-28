package com.yhsg.app.network

import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

/**
 * 后端 API 客户端。BASE_URL 开发期指向局域网主机；
 * 明文 HTTP 需配合 networkSecurityConfig（M4 上线换 HTTPS）。
 */
object ApiClient {
    // TODO(T2.1): 迁移到 BuildConfig 字段 + DataStore 服务器设置页
    const val BASE_URL = "http://192.168.1.100:8000/"
    const val TOKEN = "dev-single-user-token" // M1 单用户 token；M3 换 JWT

    val service: YingHaiApi by lazy {
        val logging = HttpLoggingInterceptor().apply { level = HttpLoggingInterceptor.Level.BASIC }
        val client = OkHttpClient.Builder()
            .addInterceptor { chain ->
                chain.proceed(
                    chain.request().newBuilder()
                        .header("Authorization", "Bearer $TOKEN")
                        .build()
                )
            }
            .addInterceptor(logging)
            .build()

        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(YingHaiApi::class.java)
    }
}
