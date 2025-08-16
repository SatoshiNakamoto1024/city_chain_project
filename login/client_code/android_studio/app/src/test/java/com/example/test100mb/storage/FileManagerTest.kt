package com.example.test100mb.storage

// app/src/androidTest/java/com/example/test100mb/storage/FileManagerTest.kt

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import java.io.File

class FileManagerTest {
    private lateinit var context: Context
    private val filename = "reserve.bin"
    private val file get() = File(context.filesDir, filename)

    @Before
    fun setUp() {
        context = ApplicationProvider.getApplicationContext()
        // もし残っていたら削除しておく
        if (file.exists()) file.delete()
    }

    @After
    fun tearDown() {
        if (file.exists()) file.delete()
    }

    @Test
    fun testReserveAndReleaseSpace() {
        // まだ存在しない
        assertFalse(file.exists())

        // 100MB を予約
        FileManager.reserveSpace(context)
        assertTrue(file.exists())
        assertEquals(FileManager.RESERVATION_SIZE, file.length())

        // 解放
        FileManager.releaseSpace(context)
        assertFalse(file.exists())
    }
}
