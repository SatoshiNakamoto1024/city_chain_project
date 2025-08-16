// File: app/src/main/java/com/example/test100mb/ui/LoginActivity.kt
package com.example.test100mb.ui

import android.content.Intent
import android.os.Bundle
import android.util.Base64
import android.widget.Button
import android.widget.EditText
import androidx.appcompat.app.AppCompatActivity
import com.example.test100mb.R
import com.example.test100mb.network.*
import com.example.test100mb.security.*
import com.example.test100mb.storage.FileManager
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response
import java.io.File
import javax.crypto.Cipher
import android.util.Log
import com.google.gson.Gson

class LoginActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_login)

        val etUser = findViewById<EditText>(R.id.etUsername)
        val etPass = findViewById<EditText>(R.id.etPassword)
        val btn    = findViewById<Button>(R.id.btnLogin)

        btn.setOnClickListener {

            /* ---------------- 認証リクエスト ---------------- */
            ApiClient.authService.login(
                LoginRequest(
                    username = etUser.text.toString(),
                    password = etPass.text.toString()
                )
            ).enqueue(object : Callback<LoginResponse> {

                override fun onResponse(
                    call : Call<LoginResponse>,
                    resp : Response<LoginResponse>
                ) {
                    val body = resp.body()
                    Log.d("LOGIN_JSON", Gson().toJson(body))
                    if (body == null || !body.success) {
                        // TODO: 認証失敗ダイアログ
                        return
                    }

                    /* ① RSA キーペア生成／読込 */
                    val (rsaPriv, _) = RsaKeyManager.ensureKeyPair(this@LoginActivity)

                    /* ② サーバーから届いた PQC 鍵・証明書を保存 */
                    KeyFileManager.storeAll(
                        context         = this@LoginActivity,
                        certPem         = body.clientCertificatePem   ?: "",
                        ntruKeyPem      = body.ntruPrivateKeyPem      ?: "",
                        dilithiumKeyPem = body.dilithiumPrivateKeyPem ?: ""
                    )

                    /* ③ Dilithium 秘密鍵を安全に取得（RSA で復号） */
                    val upd = ApiClient.keyUpdateService.updateKey(
                        KeyUpdateRequest(
                            user_uuid   = etUser.text.toString(),
                            rsa_pub_pem = RsaKeyManager.publicPem(this@LoginActivity)
                        )
                    ).execute().body() ?: run {
                        // TODO: エラー処理
                        return
                    }

                    val cipherBytes = Base64.decode(
                        upd.encrypted_secret_key_b64, Base64.DEFAULT
                    )
                    val plainSecret = Cipher
                        .getInstance("RSA/ECB/OAEPWithSHA-256AndMGF1Padding")
                        .apply { init(Cipher.DECRYPT_MODE, rsaPriv) }
                        .doFinal(cipherBytes)                 // ← “生バイト列” が得られる

                    DilithiumSecretKeyStore.save(this@LoginActivity, plainSecret)

                    /* ④ 100 MB 予約 & サーバーへ通知 */
                    FileManager.reserveSpace(this@LoginActivity)
                    ApiClient.storageService.storageCheck(
                        StorageCheckRequest(
                            userUuid      = etUser.text.toString(),
                            reservedBytes = FileManager.RESERVATION_SIZE
                        )
                    ).enqueue(object : Callback<StorageCheckResponse> {
                        override fun onResponse(
                            c: Call<StorageCheckResponse>,
                            r: Response<StorageCheckResponse>
                        ) { /* optional log */ }

                        override fun onFailure(
                            c: Call<StorageCheckResponse>,
                            t: Throwable
                        ) { /* retry? */ }
                    })

                    /* ⑤ メイン画面へ */
                    startActivity(Intent(this@LoginActivity, MainActivity::class.java))
                    finish()
                }

                override fun onFailure(call: Call<LoginResponse>, t: Throwable) {
                    // TODO: ネットワークエラー表示
                }
            })
        }
    }
}
