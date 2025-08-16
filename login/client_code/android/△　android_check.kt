// File: client_code/android_check.kt
/* 
   Androidアプリ内でストレージ容量を計測し、サーバーへ POST する Kotlin サンプル
   (実際にはAndroid Studioプロジェクト内で動かす想定)
*/

package com.example.storagecheck

import android.os.StatFs
import android.content.Context
import okhttp3.*
import org.json.JSONObject
import java.io.IOException

object StorageChecker {

    fun getFreeSpaceBytes(context: Context): Long {
        val path = context.filesDir  // アプリ内部領域
        val stat = StatFs(path.absolutePath)
        val blockSize = stat.blockSizeLong
        val availableBlocks = stat.availableBlocksLong
        return blockSize * availableBlocks
    }

    fun doLogin(context: Context, username: String, password: String) {
        val freeBytes = getFreeSpaceBytes(context)

        val jsonObj = JSONObject().apply {
            put("username", username)
            put("password", password)
            put("client_free_space", freeBytes)
        }

        val JSON = MediaType.parse("application/json; charset=utf-8")
        val requestBody = RequestBody.create(JSON, jsonObj.toString())

        val request = Request.Builder()
            .url("http://your-server-ip:5050/login")
            .header("User-Agent", "Mozilla/5.0 (Linux; Android 10; SM-G975F)")
            .post(requestBody)
            .build()

        val client = OkHttpClient()
        client.newCall(request).enqueue(object: Callback {
            override fun onFailure(call: Call, e: IOException) {
                println("Network error: ${e.message}")
            }

            override fun onResponse(call: Call, response: Response) {
                val body = response.body()?.string() ?: ""
                println("Response code=${response.code()}, body=$body")
            }
        })
    }
}
