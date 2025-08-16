// File: app/src/main/java/com/example/test100mb/security/DilithiumSigner.kt
package com.example.test100mb.security

import android.content.Context
import android.util.Base64
import org.bouncycastle.pqc.jcajce.provider.BouncyCastlePQCProvider   // ← 変更
import java.security.KeyFactory
import java.security.Security
import java.security.Signature
import java.security.spec.PKCS8EncodedKeySpec

object DilithiumSigner {

    init {
        // １度だけ PQC プロバイダを登録（優先度を上げたい場合は position=1）
        if (Security.getProvider(BouncyCastlePQCProvider.PROVIDER_NAME) == null) {
            Security.addProvider(BouncyCastlePQCProvider())
        }
    }

    /** PEM ヘッダ／フッタを除去して DER バイト列に変換 */
    private fun stripPem(pem: String): ByteArray =
        Base64.decode(
            pem.replace("-----BEGIN PRIVATE KEY-----", "")
                .replace("-----END PRIVATE KEY-----",   "")
                .replace("\\s".toRegex(), ""),
            Base64.DEFAULT
        )

    /** Dilithium 署名を生成 */
    fun sign(message: ByteArray, context: Context): ByteArray {
        // 秘密鍵 PEM をロード
        val pem            = KeyFileManager.loadDilithiumKey(context)
        val privKeyBytes   = stripPem(pem)
        val keySpec        = PKCS8EncodedKeySpec(privKeyBytes)

        // PQC プロバイダで KeyFactory / Signature を取得
        val kf      = KeyFactory.getInstance("Dilithium", BouncyCastlePQCProvider.PROVIDER_NAME)
        val privKey = kf.generatePrivate(keySpec)

        val signer  = Signature.getInstance("Dilithium", BouncyCastlePQCProvider.PROVIDER_NAME)
        signer.initSign(privKey)
        signer.update(message)
        return signer.sign()
    }
}
