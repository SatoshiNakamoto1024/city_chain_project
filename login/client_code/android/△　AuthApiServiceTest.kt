// app/src/androidTest/java/com/example/test100mb/network/AuthApiServiceTest.kt
package com.example.test100mb.network

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.example.test100mb.security.DilithiumSecretKeyStore
import org.junit.*
import org.junit.runner.RunWith
import kotlin.random.Random
import java.io.File

@RunWith(AndroidJUnit4::class)
class AuthApiServiceIntegrationTest {

    private lateinit var ctx: Context
    private lateinit var service: AuthApiService

    @Before
    fun setUp() {
        ctx = ApplicationProvider.getApplicationContext()
        /* ---------- Retrofit + OkHttp(署名Interceptor) を初期化 ---------- */
        if (!::service.isInitialized) {   // 重複初期化ガード
            ApiClient.init(ctx)
            service = ApiClient.authService
        }

        /* ---------- インターセプター用に “ダミー Dilithium SK” を置く ---------- */
        val skFile = File(ctx.filesDir, "dilithium_secret_key.pem")
        if (!skFile.exists()) {
            DilithiumSecretKeyStore.save(ctx, Random.nextBytes(2544))
        }
    }

    @Test
    fun loginSuccess_production() {
        val req  = LoginRequest("u", "p")      // ← サーバーのテストユーザーに合わせて変更
        val resp = service.login(req).execute()

        Assert.assertTrue(resp.isSuccessful)

        val body = resp.body()!!
        Assert.assertTrue(body.success)
        Assert.assertNotNull(body.rsaPrivateKey)
        Assert.assertNotNull(body.clientCertificatePem)
    }

    @Test
    fun loginFailure_production() {
        val resp = service.login(LoginRequest("invalid", "invalid")).execute()
        Assert.assertFalse(resp.isSuccessful)
    }
}
