// app/src/androidTest/java/com/example/test100mb/network/StorageApiServiceTest.kt
package com.example.test100mb.network

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.example.test100mb.security.DilithiumSecretKeyStore
import com.example.test100mb.storage.FileManager
import org.junit.*
import org.junit.runner.RunWith
import kotlin.random.Random
import java.io.File

@RunWith(AndroidJUnit4::class)
class StorageApiServiceIntegrationTest {

    private lateinit var ctx: Context
    private lateinit var service: StorageApiService

    @Before
    fun setUp() {
        ctx = ApplicationProvider.getApplicationContext()
        if (!::service.isInitialized) {
            ApiClient.init(ctx)
            service = ApiClient.storageService
        }
        // ダミー Dilithium SK（署名ヘッダ用）
        val skFile = File(ctx.filesDir, "dilithium_secret_key.pem")
        if (!skFile.exists()) {
            DilithiumSecretKeyStore.save(ctx, Random.nextBytes(2544))
        }
    }

    @Test
    fun storageCheck_production() {
        val userUuid      = "testuser-uuid"                  // ← サーバー側と合わせる
        val reservedBytes = FileManager.RESERVATION_SIZE

        val resp = service.storageCheck(
            StorageCheckRequest(userUuid, reservedBytes)
        ).execute()

        Assert.assertTrue(resp.isSuccessful)
        val body = resp.body()!!
        Assert.assertTrue(body.success)
    }
}
