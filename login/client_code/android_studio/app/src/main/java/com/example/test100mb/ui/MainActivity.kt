package com.example.test100mb.ui

// app/src/main/java/com/example/test100mb/ui/MainActivity.kt

import android.content.Intent
import android.os.Bundle
import android.util.Log
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import com.example.test100mb.R
import com.example.test100mb.network.ApiClient
import com.example.test100mb.network.StorageCheckRequest
import com.example.test100mb.network.StorageCheckResponse
import com.example.test100mb.security.KeyStoreManager
import com.example.test100mb.storage.FileManager
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class MainActivity : AppCompatActivity() {

    private val TAG = "MainActivity"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        val statusText = findViewById<TextView>(R.id.statusText)
        val btnReserve = findViewById<Button>(R.id.reserveButton)
        val btnLogout = findViewById<Button>(R.id.btnLogout)

        btnReserve.setOnClickListener {
            statusText.text = "Reserving 100MB..."
            try {
                FileManager.reserveSpace(this)
                statusText.text = "100MB reserved successfully."

                val userUuid = "test-user-uuid-1234"  // 実運用ではユーザー情報から取得
                val reservedBytes = FileManager.RESERVATION_SIZE

                ApiClient.storageService
                    .storageCheck(StorageCheckRequest(userUuid, reservedBytes))
                    .enqueue(object : Callback<StorageCheckResponse> {
                        override fun onResponse(
                            call: Call<StorageCheckResponse>,
                            response: Response<StorageCheckResponse>
                        ) {
                            val body = response.body()
                            if (response.isSuccessful && body?.success == true) {
                                statusText.text = "サーバー通知成功: ${body.message}"
                            } else {
                                statusText.text = "通知失敗: ${body?.message ?: "no response"}"
                            }
                        }

                        override fun onFailure(call: Call<StorageCheckResponse>, t: Throwable) {
                            Log.e(TAG, "通知エラー: ${t.message}")
                            statusText.text = "通信エラー: ${t.message}"
                        }
                    })

            } catch (e: Exception) {
                Log.e(TAG, "予約失敗: ${e.message}")
                statusText.text = "100MB予約失敗: ${e.message}"
            }
        }

        btnLogout.setOnClickListener {
            FileManager.releaseSpace(this)
            startActivity(Intent(this, LoginActivity::class.java))
            finish()
        }
    }
}