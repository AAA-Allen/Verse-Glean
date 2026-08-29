package com.yhsg.app.network

import okhttp3.MultipartBody
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.PATCH
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.Query

/**
 * 后端接口定义，契约唯一来源 docs/API.md；字段变更必须先改文档。
 */
interface YingHaiApi {

    @POST("api/v1/extractions")
    suspend fun createExtraction(@Body body: ExtractionCreate): ApiEnvelope<TaskData>

    /** T3.7 音频捕获：wav 上传（后端 ASR → 胶囊）。 */
    @Multipart
    @POST("api/v1/extractions/audio")
    suspend fun uploadAudio(@Part file: MultipartBody.Part): ApiEnvelope<TaskData>

    @POST("api/v1/extractions/{taskId}/manual-text")
    suspend fun retryWithManualText(
        @Path("taskId") taskId: String,
        @Body body: ManualRetry,
    ): ApiEnvelope<TaskData>

    @GET("api/v1/extractions/{taskId}")
    suspend fun getTask(@Path("taskId") taskId: String): ApiEnvelope<TaskData>

    @GET("api/v1/capsules")
    suspend fun listCapsules(
        @Query("page") page: Int = 1,
        @Query("page_size") pageSize: Int = 20,
        @Query("tag") tag: String? = null,
    ): ApiEnvelope<CapsuleListData>

    @GET("api/v1/capsules/{capsuleId}")
    suspend fun getCapsule(@Path("capsuleId") id: Long): ApiEnvelope<CapsuleData>

    @PATCH("api/v1/capsules/{capsuleId}")
    suspend fun updateCapsule(
        @Path("capsuleId") id: Long,
        @Body body: CapsuleUpsert,
    ): ApiEnvelope<CapsuleData>
}
