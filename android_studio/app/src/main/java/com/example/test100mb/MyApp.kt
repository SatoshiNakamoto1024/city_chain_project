package com.example.test100mb

// app/src/main/java/com/example/test100mb/MyApp.kt // ← ここの名前は必ず合わせる

import android.app.Application
import com.example.test100mb.network.ApiClient

class MyApp : Application() {
    override fun onCreate() {
        super.onCreate()
        // Retrofit + OkHttp(署名Interceptor) を一度だけ初期化
        ApiClient.init(this)
    }
}
