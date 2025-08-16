// app/src/main/java/com/example/test100mb/network/ApiClient.kt
package com.example.test100mb.network

import android.content.Context
import com.example.test100mb.network.HttpSignatureInterceptor
import okhttp3.OkHttpClient
import com.google.gson.annotations.SerializedName
import java.util.concurrent.TimeUnit
import retrofit2.Call
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.POST

/* ─────────────────────────────────── */
/*  ① Register エンドポイント定義      */
/* ─────────────────────────────────── */
interface RegisterApiService {

    // ★ 末尾スラッシュを付けない「ルート」
    @POST("register/")                // ← ここを修正
    fun register(
        @Body body: RegisterRequest
    ): Call<RegisterResponse>
}

/* リクエスト／レスポンスのデータモデル */
data class RegisterRequest(
    val username: String,
    val email:    String,
    val password: String
)

data class RegisterResponse(
    val success:        Boolean,
    val uuid:           String,
    /* ↓ サーバーが返す JSON 名に合わせて下さい */
    @SerializedName("client_cert")   // ←★追加
    val clientCertPem: String? = null,          // null 許容
    // username も来ない場合があるので nullable
    val username: String? = null
    // ほか必要なら追記
)

/* ─────────────────────────────────── */
/*  ② 共通 ApiClient シングルトン      */
/* ─────────────────────────────────── */
object ApiClient {

    /** テスト環境のベース URL */
    private const val BASE_URL = "http://192.168.3.8:8888/"

    /** Retrofit は遅延初期化 → null チェックを避けるため lateinit */
    private lateinit var retrofit: Retrofit

    /* サービスごとに backing-field を持つ */
    private lateinit var _authService:      AuthApiService
    private lateinit var _storageService:   StorageApiService
    private lateinit var _keyUpdateService: KeyUpdateApiService
    private lateinit var _registerService:  RegisterApiService

    /** Application#onCreate など **1 回だけ** 呼び出す */
    fun init(ctx: Context) {

        /* ---- OkHttp ---- */
        val ok = OkHttpClient.Builder()
            .connectTimeout(10,  TimeUnit.SECONDS)      // そのまま
            .readTimeout   (60,  TimeUnit.SECONDS)      // ←★ 60 秒に拡大
            .writeTimeout  (60,  TimeUnit.SECONDS)      // ←★ 同上
            .addInterceptor(HttpSignatureInterceptor(ctx))  // 署名ヘッダを付与
            .build()

        /* ---- Retrofit ---- */
        retrofit = Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(ok)
            .addConverterFactory(GsonConverterFactory.create())
            .build()

        /* ---- 各 API インターフェースを生成 ---- */
        _authService      = retrofit.create(AuthApiService     ::class.java)
        _storageService   = retrofit.create(StorageApiService  ::class.java)
        _keyUpdateService = retrofit.create(KeyUpdateApiService::class.java)
        _registerService  = retrofit.create(RegisterApiService ::class.java)
    }

    /* ---- public getter ---- */
    val authService      get() = _authService
    val storageService   get() = _storageService
    val keyUpdateService get() = _keyUpdateService
    val registerService  get() = _registerService
}
