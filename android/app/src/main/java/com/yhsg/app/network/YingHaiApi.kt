package com.yhsg.app.network

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

/**
 * 后端接口定义，契约唯一来源 docs/API.md；字段变更必须先改文档。
 */
interface YingHaiApi {

    @POST("api/v1/extractions")
    suspend fun createExtraction(@Body body: ExtractionCreate): ApiEnvelope<TaskData>

    @GET("api/v1/extractions/{taskId}")
    suspend fun getTask(@Path("taskId") taskId: String): ApiEnvelope<TaskData>

    @GET("api/v1/capsules/{capsuleId}")
    suspend fun getCapsule(@Path("capsuleId") id: Long): ApiEnvelope<CapsuleData>

    @GET("api/v1/capsules")
    suspend fun listCapsules(
        @retrofit2.http.Query("page") page: Int = 1,
        @retrofit2.http.Query("page_size") pageSize: Int = 20,
    ): ApiEnvelope<CapsuleListData>
}
