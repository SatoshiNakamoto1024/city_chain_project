package com.example.test100mb.network.model

/**
 *  /register/ エンドポイントのリクエスト／レスポンス DTO
 */

/* ---- リクエスト ---- */
data class RegisterRequest(
    val username: String,
    val email: String,
    val password: String
)

/* ---- レスポンス ---- */
data class RegisterResponse(
    val success: Boolean,
    val uuid: String,
    val username: String,   // ★ 追加
    val clientCertPem: String,
    // 以下は必要に応じて追加
    val fingerprint: String?           = null,
    val message: String?               = null,
    val dilithiumSecretKey: String?    = null,   // hex 文字列 or Base64
    val rsaPrivateKey: String?         = null,   // Base64(PEM)
)
