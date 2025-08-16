// File: app/src/main/java/com/example/test100mb/security/RsaKeyManager.kt
package com.example.test100mb.security

import android.content.Context
import java.io.File
import java.security.KeyPairGenerator
import java.security.PrivateKey
import java.security.PublicKey
import android.util.Base64

object RsaKeyManager {
    private const val RSA_DIR = "rsa"
    private const val PRIV = "rsa_private_key.pem"
    private const val PUB  = "rsa_public_key.pem"

    /**
     * filesDir/rsa/ 下に 2048bit RSA キーペアを生成して PEM で保存
     * すでにあれば読み込むだけ
     */
    fun ensureKeyPair(ctx: Context): Pair<PrivateKey, PublicKey> {
        val dir = File(ctx.filesDir, RSA_DIR).apply { mkdirs() }
        val privFile = File(dir, PRIV)
        val pubFile  = File(dir, PUB)

        return if (privFile.exists() && pubFile.exists()) {
            PemUtils.readRsaKeyPair(privFile, pubFile)
        } else {
            val kp = KeyPairGenerator.getInstance("RSA").apply { initialize(2048) }.genKeyPair()
            PemUtils.writePem(privFile, "PRIVATE KEY", kp.private.encoded)
            PemUtils.writePem(pubFile , "PUBLIC KEY",  kp.public.encoded)
            kp.private to kp.public
        }
    }

    fun publicPem(ctx: Context): String =
        File(ctx.filesDir, "$RSA_DIR/$PUB").readText(Charsets.US_ASCII)
}
