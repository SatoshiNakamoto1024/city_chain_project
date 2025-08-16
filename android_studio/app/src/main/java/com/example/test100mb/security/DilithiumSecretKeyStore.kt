// File: app/src/main/java/com/example/test100mb/security/DilithiumSecretKeyStore.kt
package com.example.test100mb.security

import android.content.Context
import java.io.File

object DilithiumSecretKeyStore {
    private const val FILE_NAME = "dilithium_secret_key.pem"

    /** SK を保存（上書き） */
    fun save(ctx: Context, bytes: ByteArray) =
        ctx.openFileOutput(FILE_NAME, Context.MODE_PRIVATE).use { it.write(bytes) }

    /** SK を必ず取得。無ければ例外を投げる */
    fun load(ctx: Context): ByteArray =
        File(ctx.filesDir, FILE_NAME).takeIf { it.exists() }
            ?.readBytes()
            ?: throw IllegalStateException("Dilithium SK not found")

    /** SK をオプションで取得。無ければ null */
    fun loadOrNull(ctx: Context): ByteArray? =
        File(ctx.filesDir, FILE_NAME).takeIf { it.exists() }?.readBytes()

    /** 単に存在確認だけしたいとき用 */
    fun exists(ctx: Context): Boolean =
        File(ctx.filesDir, FILE_NAME).exists()
}
