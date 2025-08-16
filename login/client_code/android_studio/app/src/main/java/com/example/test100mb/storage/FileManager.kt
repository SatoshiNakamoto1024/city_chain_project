package com.example.test100mb.storage

//  app/src/main/java/com/example/test100mb/storage/FileManager.kt

import android.content.Context
import java.io.File
import java.io.RandomAccessFile

object FileManager {
    private const val RESERVATION_FILE = "reserve.bin"
    const val RESERVATION_SIZE = 100L * 1024 * 1024  // 100MB

    fun reserveSpace(context: Context) {
        val f = File(context.filesDir, RESERVATION_FILE)
        RandomAccessFile(f, "rw").use { raf ->
            raf.setLength(RESERVATION_SIZE)
        }
    }

    fun releaseSpace(context: Context) {
        val f = File(context.filesDir, RESERVATION_FILE)
        if (f.exists()) f.delete()
    }
}
