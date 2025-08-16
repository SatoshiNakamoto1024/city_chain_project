package com.example.test100mb.storage

// app/src/androidTest/java/com/example/test100mb/storage/FileManagerTest.kt

import android.content.Context
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.example.test100mb.storage.FileManager
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

/**
 * 実際の Android コンテキストを使ったインストルメンテーションテスト
 */
@RunWith(AndroidJUnit4::class)
class FileManagerTest {
    private lateinit var context: Context
    private val filename = "reserve.bin"
    private val file: File
        get() = File(context.filesDir, filename)

    @Before
    fun setUp() {
        // インストルメンテーション環境のコンテキストを取得
        context = InstrumentationRegistry.getInstrumentation().targetContext
        // もし前回のテストで残っていれば削除
        if (file.exists()) file.delete()
    }

    @After
    fun tearDown() {
        // テスト後にファイルが残っていれば削除
        if (file.exists()) file.delete()
    }

    @Test
    fun testReserveAndReleaseSpace() {
        // 初期状態では存在しない
        assertFalse(file.exists())

        // 100MB を予約
        FileManager.reserveSpace(context)
        assertTrue(file.exists())
        assertEquals(FileManager.RESERVATION_SIZE, file.length())

        // 予約解放
        FileManager.releaseSpace(context)
        assertFalse(file.exists())
    }
}
