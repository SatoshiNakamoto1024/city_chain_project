// app/src/main/java/com/example/test100mb/network/AuthApiService.kt
package com.example.test100mb.network

import retrofit2.Call
import retrofit2.http.Body
import retrofit2.http.POST

/* ───────────── データモデル ───────────── */

data class LoginRequest(
    val username: String,
    val password: String
)

data class LoginResponse(
    val success: Boolean,

    /* 署名鍵一式（無い場合は null） */
    val rsaPrivateKey:        String?,   // Base64-PEM
    val clientCertificatePem: String?,   // NTRU + Dilithium 合成 PEM
    val ntruPrivateKeyPem:    String?,   // NTRU   秘密鍵 PEM
    val dilithiumPrivateKeyPem: String?, // Dilithium 秘密鍵 PEM

    val message: String?                 // サーバー側のメッセージ
)

/* ─────────── Retrofit IF ──────────── */

interface AuthApiService {

    /** Flask 側の `/user/login` (POST) に対応 */
    @POST("/user/login")
    fun login(
        @Body req: LoginRequest
    ): Call<LoginResponse>
}
