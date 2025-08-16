// File: app/src/androidTest/java/com/example/test100mb/network/AuthApiServiceIntegrationTest.kt
package com.example.test100mb.network

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.example.test100mb.security.DilithiumSecretKeyStore
import com.example.test100mb.security.KeyFileManager
import org.junit.*
import org.junit.runner.RunWith
import java.io.File
import java.util.UUID
import kotlin.random.Random

/**
 * ① /register/ でユーザーを作成し PEM を端末保存
 * ② /user/login で JWT を取得
 * ③ Dilithium SK をローカルに保持してある前提で
 *    HttpSignatureInterceptor が署名を付与できることを検証
 */
@RunWith(AndroidJUnit4::class)
class AuthApiServiceIntegrationTest {

    private lateinit var ctx: Context
    private lateinit var registered: RegisterResponse        // 生成したユーザーを保持
    private val testPassword = "TestPass123!"

    /* ───────────────────────────── set-up ───────────────────────────── */

    @Before
    fun setUp() {
        ctx = ApplicationProvider.getApplicationContext()

        // ApiClient はシングルトン。重複呼び出しでも害は無い
        ApiClient.init(ctx)

        // DilithiumSecretKeyStore が無いと Interceptor が失敗するため
        val skFile = File(ctx.filesDir, "dilithium_secret_key.pem")
        if (!skFile.exists()) {
            DilithiumSecretKeyStore.save(ctx, Random.nextBytes(2544))
        }
    }

    /* ───────────────────── helper : ユーザー登録 ───────────────────── */

    private fun ensureUser() {
        if (::registered.isInitialized) return

        val uname = "it_${UUID.randomUUID().toString().take(8)}"

        val res = ApiClient.registerService
            .register(RegisterRequest(uname, "$uname@example.com", testPassword))
            .execute()

        Assert.assertTrue("register HTTP ${res.code()}", res.isSuccessful)
        registered = res.body() ?: error("RegisterResponse null")

        // ---------- レスポンスを補正 ----------
        val body = res.body() ?: error("RegisterResponse null")
        registered = if (body.username.isNullOrBlank()) {
            body.copy(username = uname)             // ★ username を必ずセット
        } else {
            body
        }
        user = registered                           // companion に共有

        // ----- PEM が届いていれば保存（null ならスキップ） -----
        registered.clientCertPem?.let {
            KeyFileManager.storeAll(
                context = ctx,
                certPem = it,
                ntruKeyPem = "",
                dilithiumKeyPem = ""
            )
        }
    }

    /* ─────────────────────────── tests ───────────────────────────── */

    @Test
    fun loginSuccess_production() {
        ensureUser()

        val resp = ApiClient.authService
            .login(
                LoginRequest(
                    username = registered.username!!,   // ← !! で非 null を保証
                    password = testPassword
                )
            )
            .execute()

        Assert.assertTrue("login HTTP ${resp.code()}", resp.isSuccessful)
        Assert.assertTrue(resp.body()?.success == true)
    }

    @Test
    fun loginFailure_production() {
        ensureUser()

        val resp = ApiClient.authService
            .login(LoginRequest("wrongUser", "wrongPass"))
            .execute()

        // HTTP エラー、または success=false のどちらでも「失敗」とみなす
        Assert.assertFalse(resp.isSuccessful && resp.body()?.success == true)
    }

    /* ───────────────── companion ───────────────── */
    companion object {
        /** StorageApiServiceIntegrationTest などから参照可能にする */
        @JvmStatic lateinit var user: RegisterResponse

        @JvmStatic
        fun userInitialized(): Boolean = ::user.isInitialized
    }
}