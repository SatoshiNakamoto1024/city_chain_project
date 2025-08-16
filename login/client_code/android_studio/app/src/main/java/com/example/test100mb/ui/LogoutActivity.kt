package com.example.test100mb.ui

// app/src/main/java/com/example/test100mb/ui/LogoutActivity.kt

import android.content.Intent
import android.os.Bundle
import android.util.Log
import androidx.appcompat.app.AppCompatActivity
import com.example.test100mb.network.ApiClient
import com.example.test100mb.network.StorageCheckRequest
import com.example.test100mb.network.StorageCheckResponse
import com.example.test100mb.storage.FileManager
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class LogoutActivity : AppCompatActivity() {

    private val TAG = "LogoutActivity"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // まず予約ファイルを削除
        FileManager.releaseSpace(this)

        // もし通知が必要であれば、サーバーに「ログアウト済み・解放済み」として通知（任意）
        val userUuid = "test-user-uuid-1234"  // 本番ではログイン状態から取得
        ApiClient.storageService
            .storageCheck(StorageCheckRequest(userUuid, 0L)) // 0バイトにリセット通知
            .enqueue(object : Callback<StorageCheckResponse> {
                override fun onResponse(
                    call: Call<StorageCheckResponse>,
                    response: Response<StorageCheckResponse>
                ) {
                    Log.i(TAG, "ログアウト時通知成功: ${response.body()?.message}")
                }

                override fun onFailure(call: Call<StorageCheckResponse>, t: Throwable) {
                    Log.e(TAG, "ログアウト通知失敗: ${t.message}")
                }
            })

        // Login画面へ戻す
        startActivity(Intent(this, LoginActivity::class.java))
        finish()
    }
}
