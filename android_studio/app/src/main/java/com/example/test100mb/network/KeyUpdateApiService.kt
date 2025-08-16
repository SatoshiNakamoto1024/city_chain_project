// app/src/main/java/com/example/test100mb/network/KeyUpdateApiService.kt
package com.example.test100mb.network

import retrofit2.Call
import retrofit2.http.Body
import retrofit2.http.POST

data class KeyUpdateRequest(
    val user_uuid:   String,
    val rsa_pub_pem: String
)

data class KeyUpdateResponse(
    /** RSA で暗号化された Dilithium 秘密鍵 (Base64) */
    val encrypted_secret_key_b64: String
)

interface KeyUpdateApiService {

    /** Flask 側 `/user/keys/update` */
    @POST("/user/keys/update")
    fun updateKey(
        @Body req: KeyUpdateRequest
    ): Call<KeyUpdateResponse>
}
