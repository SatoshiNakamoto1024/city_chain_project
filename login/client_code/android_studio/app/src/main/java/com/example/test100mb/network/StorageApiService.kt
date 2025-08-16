// app/src/main/java/com/example/test100mb/network/StorageApiService.kt
package com.example.test100mb.network

import retrofit2.Call
import retrofit2.http.Body
import retrofit2.http.POST

data class StorageCheckRequest(
    val userUuid:      String,
    val reservedBytes: Long
)

data class StorageCheckResponse(
    val success: Boolean,
    val message: String?
)

interface StorageApiService {

    /** Flask 側 `/user/storage_check` */
    @POST("/user/storage_check")
    fun storageCheck(
        @Body req: StorageCheckRequest
    ): Call<StorageCheckResponse>
}
