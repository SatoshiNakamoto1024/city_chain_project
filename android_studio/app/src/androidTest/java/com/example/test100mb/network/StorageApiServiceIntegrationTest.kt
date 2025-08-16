// app/src/androidTest/java/com/example/test100mb/network/StorageApiServiceIntegrationTest.kt
package com.example.test100mb.network

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.example.test100mb.storage.FileManager
import org.junit.*
import org.junit.runner.RunWith
import java.util.UUID

/**
 * /user/storage_check を叩いて 200 / success=true を確認する E2E テスト
 */
@RunWith(AndroidJUnit4::class)
class StorageApiServiceIntegrationTest {

    private lateinit var ctx: Context

    @Before
    fun setUp() {
        ctx = ApplicationProvider.getApplicationContext()
        ApiClient.init(ctx)

        /* まだ登録済みユーザーが無ければ 1 件だけ作成して共有する */
        if (!AuthApiServiceIntegrationTest.userInitialized()) {
            val uname = "st_${UUID.randomUUID().toString().take(8)}"
            val res = ApiClient.registerService
                .register(RegisterRequest(uname, "$uname@example.com", "TestPass123!"))
                .execute()

            Assert.assertTrue("register HTTP ${res.code()}", res.isSuccessful)
            AuthApiServiceIntegrationTest.user =
                res.body()!!.copy(username = uname)   // ← companion にセット
        }
    }

    @Test
    fun storageCheck_production() {
        val user = AuthApiServiceIntegrationTest.user

        val resp = ApiClient.storageService.storageCheck(
            StorageCheckRequest(
                userUuid      = user.uuid,
                reservedBytes = FileManager.RESERVATION_SIZE
            )
        ).execute()

        Assert.assertTrue("HTTP ${resp.code()}", resp.isSuccessful)
        Assert.assertTrue(resp.body()?.success == true)
    }
}
