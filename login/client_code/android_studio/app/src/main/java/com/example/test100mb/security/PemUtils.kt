// File: app/src/main/java/com/example/test100mb/security/PemUtils.kt
package com.example.test100mb.security

import android.util.Base64
import java.io.File
import java.security.KeyFactory
import java.security.PrivateKey
import java.security.PublicKey
import java.security.spec.PKCS8EncodedKeySpec
import java.security.spec.X509EncodedKeySpec

object PemUtils {

    /** DER → PEM ファイル出力 */
    fun writePem(dst: File, type: String, bytes: ByteArray) {
        // ★ Base64.NO_WRAP で改行なしエンコード
        val b64 = Base64.encodeToString(bytes, Base64.NO_WRAP)
        dst.writeText(buildString {
            append("-----BEGIN $type-----\n")
            for (chunk in b64.chunked(64)) append(chunk).append('\n')
            append("-----END $type-----\n")
        })
    }

    /** PEM 形式の RSA キーペアを読み込む */
    fun readRsaKeyPair(priv: File, pub: File): Pair<PrivateKey, PublicKey> {
        val privBytes = decodePem(priv.readText())
        val pubBytes  = decodePem(pub.readText())
        val kf = KeyFactory.getInstance("RSA")
        val prv = kf.generatePrivate(PKCS8EncodedKeySpec(privBytes))
        val pb  = kf.generatePublic (X509EncodedKeySpec (pubBytes))
        return prv to pb
    }

    /** PEM 本文 → DER バイト列 */
    private fun decodePem(pem: String): ByteArray =
        Base64.decode(
            pem.lineSequence()
                .filter { it.isNotBlank() && !it.startsWith("-----") }
                .joinToString(""),
            Base64.DEFAULT
        )
}
