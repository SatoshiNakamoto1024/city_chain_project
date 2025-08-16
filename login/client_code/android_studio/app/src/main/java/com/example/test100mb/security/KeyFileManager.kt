// File: app/src/main/java/com/example/test100mb/security/KeyFileManager.kt
package com.example.test100mb.security

import android.content.Context
import java.io.File
import java.nio.charset.StandardCharsets

/**
 * クライアント証明書と PQC 秘密鍵を端末内ストレージに保存・読込するユーティリティ
 *
 * すべて Context#getFilesDir() (= /data/data/<pkg>/files) 直下に配置。
 * MODE_PRIVATE で書き込むので他アプリからは参照できない。
 *
 * ─ 保存ファイル名 ───────────────────────────────
 *   client_certificate.pem   … 合成 PEM (NTRU + Dilithium)
 *   ntru_private_key.pem     … NTRU 秘密鍵 PEM      (省略可)
 *   dilithium_private_key.pem… Dilithium 秘密鍵 PEM (省略可)
 * ──────────────────────────────────────────────
 *
 * ※ 本番では Android Keystore などへの移行を検討してください。
 */
object KeyFileManager {

    private const val CERT_FILE       = "client_certificate.pem"
    private const val NTRU_KEY_FILE   = "ntru_private_key.pem"
    private const val DILITHIUM_FILE  = "dilithium_private_key.pem"

    /* ------------ 保存系 ------------ */

    /**
     * 3 つまとめて保存するヘルパ。
     * 空文字列が渡された鍵はスキップする（既存を残したいとき用）。
     */
    fun storeAll(
        context: Context,
        certPem: String,
        ntruKeyPem: String = "",
        dilithiumKeyPem: String = ""
    ) {
        write(context, CERT_FILE, certPem)
        if (ntruKeyPem.isNotBlank())      write(context, NTRU_KEY_FILE,  ntruKeyPem)
        if (dilithiumKeyPem.isNotBlank()) write(context, DILITHIUM_FILE, dilithiumKeyPem)
    }

    /* ------------ 取得系 ------------ */

    fun loadCertificate(context: Context): String =
        readOrEmpty(context, CERT_FILE)

    fun loadNtruKey(context: Context): String =
        readOrEmpty(context, NTRU_KEY_FILE)

    fun loadDilithiumKey(context: Context): String =
        readOrEmpty(context, DILITHIUM_FILE)

    /* ------------ 内部ヘルパ ------------ */

    private fun write(ctx: Context, name: String, data: String) {
        ctx.openFileOutput(name, Context.MODE_PRIVATE)
            .use { it.write(data.toByteArray(StandardCharsets.UTF_8)) }
    }

    private fun readOrEmpty(ctx: Context, name: String): String {
        val f = File(ctx.filesDir, name)
        return if (f.exists()) f.readText(StandardCharsets.UTF_8) else ""
    }
}
