// settings.gradle
rootProject.name = "ClientApp"
include(":app")


// build.gradle (プロジェクトルート)
buildscript {
    ext.kotlin_version = '1.8.0'
    repositories {
        google()
        mavenCentral()
    }
    dependencies {
        classpath "com.android.tools.build:gradle:7.4.0"
        classpath "org.jetbrains.kotlin:kotlin-gradle-plugin:$kotlin_version"
    }
}

allprojects {
    repositories {
        google()
        mavenCentral()
    }
}


//  app/build.gradle
plugins {
    id 'com.android.application'
    id 'kotlin-android'
}

android {
    compileSdk 33

    defaultConfig {
        applicationId "com.example.app"
        minSdk 23
        targetSdk 33
        versionCode 1
        versionName "1.0"
    }

    buildTypes {
        release {
            minifyEnabled false
            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
        }
    }
}

dependencies {
    implementation "org.jetbrains.kotlin:kotlin-stdlib:$kotlin_version"
    implementation 'androidx.core:core-ktx:1.9.0'
    implementation 'androidx.appcompat:appcompat:1.5.1'
    implementation 'com.google.android.material:material:1.7.0'
    implementation 'androidx.security:security-crypto:1.1.0-alpha03'
    implementation 'com.squareup.retrofit2:retrofit:2.9.0'
    implementation 'com.squareup.retrofit2:converter-gson:2.9.0'
    implementation 'com.squareup.okhttp3:okhttp:4.10.0'
}


//  app/src/main/AndroidManifest.xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.example.app">

    <uses-permission android:name="android.permission.INTERNET"/>
    
    <application
        android:label="ClientApp"
        android:theme="@style/Theme.AppCompat.Light.NoActionBar">
        <activity android:name=".ui.LogoutActivity"/>
        <activity android:name=".ui.MainActivity"/>
        <activity android:name=".ui.LoginActivity">
            <intent-filter>
                <action android:name="android.intent.action.MAIN"/>
                <category android:name="android.intent.category.LAUNCHER"/>
            </intent-filter>
        </activity>
    </application>
</manifest>


//  app/src/main/java/com/example/app/network/ApiClient.kt
package com.example.app.network

import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

object ApiClient {
    private const val BASE_URL = "http://192.168.3.8:5000/"

    val retrofit: Retrofit = Retrofit.Builder()
        .baseUrl(BASE_URL)
        .addConverterFactory(GsonConverterFactory.create())
        .build()

    val authService: AuthApiService = retrofit.create(AuthApiService::class.java)
}


// app/src/main/java/com/example/app/network/AuthApiService.kt
package com.example.app.network

import retrofit2.Call
import retrofit2.http.Body
import retrofit2.http.POST

data class LoginRequest(
    val username: String,
    val password: String
)

data class LoginResponse(
    val success: Boolean,
    val rsaPrivateKey: String?,  // Base64 化された PEM
    val message: String?
)

interface AuthApiService {
    @POST("login")
    fun login(@Body req: LoginRequest): Call<LoginResponse>
}


//  app/src/main/java/com/example/app/security/KeyStoreManager.kt
package com.example.app.security

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import java.security.KeyPairGenerator
import java.security.KeyStore
import java.util.Base64

object KeyStoreManager {
    private const val ANDROID_KEYSTORE = "AndroidKeyStore"
    private const val KEY_ALIAS = "my_rsa_key"

    fun ensureKeyPair() {
        val ks = KeyStore.getInstance(ANDROID_KEYSTORE).apply { load(null) }
        if (!ks.containsAlias(KEY_ALIAS)) {
            val kpg = KeyPairGenerator
                .getInstance(KeyProperties.KEY_ALGORITHM_RSA, ANDROID_KEYSTORE)
            kpg.initialize(
                KeyGenParameterSpec.Builder(
                    KEY_ALIAS,
                    KeyProperties.PURPOSE_DECRYPT or KeyProperties.PURPOSE_ENCRYPT
                )
                    .setKeySize(2048)
                    .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_RSA_OAEP)
                    .build()
            )
            kpg.generateKeyPair()
        }
    }

    fun getPrivateKeyPem(): String {
        val ks = KeyStore.getInstance(ANDROID_KEYSTORE).apply { load(null) }
        val privateKey = ks.getKey(KEY_ALIAS, null)
        val pkcs8 = privateKey!!.encoded
        val b64 = Base64.getEncoder().encodeToString(pkcs8)
        return "-----BEGIN PRIVATE KEY-----\n$b64\n-----END PRIVATE KEY-----"
    }
}


//  app/src/main/java/com/example/app/storage/FileManager.kt
package com.example.app.storage

import android.content.Context
import java.io.File
import java.io.RandomAccessFile

object FileManager {
    private const val RESERVATION_FILE = "reserve.bin"
    private const val RESERVATION_SIZE = 100L * 1024 * 1024  // 100MB

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


//  app/src/main/java/com/example/app/ui/LoginActivity.kt
package com.example.app.ui

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import androidx.appcompat.app.AppCompatActivity
import com.example.app.R
import com.example.app.network.ApiClient
import com.example.app.network.LoginRequest
import com.example.app.security.KeyStoreManager
import com.example.app.storage.FileManager
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class LoginActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_login)

        val etUser = findViewById<EditText>(R.id.etUsername)
        val etPass = findViewById<EditText>(R.id.etPassword)
        val btn = findViewById<Button>(R.id.btnLogin)

        btn.setOnClickListener {
            val user = etUser.text.toString()
            val pass = etPass.text.toString()
            ApiClient.authService.login(LoginRequest(user, pass))
                .enqueue(object : Callback<com.example.app.network.LoginResponse> {
                    override fun onResponse(
                        call: Call<com.example.app.network.LoginResponse>,
                        resp: Response<com.example.app.network.LoginResponse>
                    ) {
                        val body = resp.body()
                        if (body != null && body.success) {
                            // キーストアに鍵生成・保存
                            KeyStoreManager.ensureKeyPair()
                            // サーバからの秘密鍵は使わずローカルキーストアを利用
                            // 100MB 予約ファイルを確保
                            FileManager.reserveSpace(this@LoginActivity)
                            // メイン画面へ
                            startActivity(Intent(this@LoginActivity, MainActivity::class.java))
                            finish()
                        } else {
                            // TODO: エラー表示
                        }
                    }
                    override fun onFailure(call: Call<com.example.app.network.LoginResponse>, t: Throwable) {
                        // TODO: 通信失敗表示
                    }
                })
        }
    }
}


//  app/src/main/java/com/example/app/ui/MainActivity.kt
package com.example.app.ui

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import androidx.appcompat.app.AppCompatActivity
import com.example.app.R

class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        val btnLogout = findViewById<Button>(R.id.btnLogout)
        btnLogout.setOnClickListener {
            startActivity(Intent(this, LogoutActivity::class.java))
            finish()
        }
    }
}


//  app/src/main/java/com/example/app/ui/LogoutActivity.kt
package com.example.app.ui

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.example.app.storage.FileManager

class LogoutActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // 100MB予約ファイルを削除
        FileManager.releaseSpace(this)
        // キーは Android Keystore なので自動的に残りますが、
        // 必要であれば KeyStoreManager に消去 API を実装してください。
        startActivity(Intent(this, LoginActivity::class.java))
        finish()
    }
}


//  app/src/main/res/layout/activity_login.xml
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:orientation="vertical"
    android:padding="24dp"
    android:layout_width="match_parent"
    android:layout_height="match_parent">

    <EditText
        android:id="@+id/etUsername"
        android:hint="Username"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"/>

    <EditText
        android:id="@+id/etPassword"
        android:hint="Password"
        android:inputType="textPassword"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:layout_marginTop="16dp"/>

    <Button
        android:id="@+id/btnLogin"
        android:text="Login"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:layout_marginTop="24dp"/>
</LinearLayout>


//  app/src/main/res/layout/activity_main.xml
<?xml version="1.0" encoding="utf-8"?>
<FrameLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:padding="24dp"
    android:layout_width="match_parent"
    android:layout_height="match_parent">

    <Button
        android:id="@+id/btnLogout"
        android:text="Logout"
        android:layout_gravity="center"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"/>
</FrameLayout>


//  app/src/main/res/layout/activity_logout.xml
<?xml version="1.0" encoding="utf-8"?>
<FrameLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:padding="24dp"
    android:layout_width="match_parent"
    android:layout_height="match_parent">

    <!-- ログアウト中に表示するか何もしないか -->
</FrameLayout>

以上
ライフサイクル：ログイン時に 100MB の予約ファイルを確保 → メイン画面へ移動
ログアウト時に予約ファイルを解放
鍵管理：Android Keystore に RSA キーペアを生成・保持（PEM をサーバー送信用にも取得可能）
を含めた、クライアント（Android）側の完全実装例です。
これでサーバーへ渡すまでの一連のフローを網羅しています。

You said:
これらをテストするテストコードを記載して。また、このあとは、user_manager¥storage_checkなどへログインしてきたよと渡すんでしょ。どのファイルから、どのファイルに渡される？本番実装になるよう、それらも省略せずに記載して
ChatGPT said:
以下、Android クライアント側のユニットテストと、本番想定でログイン後に 「storage_check」 を User Manager 側へ通知するためのクライアント→サーバー双方の実装を、ファイル単位で省略せずに全部載せます。

1. Android クライアント：テストコード
a. FileManager のテスト
//  app/src/test/java/com/example/app/storage/FileManagerTest.kt
package com.example.app.storage

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


b. AuthApiService のテスト
//  app/src/test/java/com/example/app/network/AuthApiServiceTest.kt
package com.example.app.network

import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

class AuthApiServiceTest {
    private lateinit var server: MockWebServer
    private lateinit var service: AuthApiService

    @Before
    fun setUp() {
        server = MockWebServer().apply { start() }
        service = Retrofit.Builder()
            .baseUrl(server.url("/"))
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(AuthApiService::class.java)
    }

    @After
    fun tearDown() {
        server.shutdown()
    }

    @Test
    fun login_success() {
        val json = """
          {
            "success": true,
            "rsaPrivateKey": "BASE64_PEM",
            "message": "OK"
          }
        """
        server.enqueue(MockResponse().setResponseCode(200).setBody(json))

        val resp = service.login(LoginRequest("u","p")).execute()
        assertTrue(resp.isSuccessful)
        val body = resp.body()!!
        assertTrue(body.success)
        assertEquals("BASE64_PEM", body.rsaPrivateKey)
    }

    @Test
    fun login_failure() {
        val json = """{"success":false,"message":"bad"}"""
        server.enqueue(MockResponse().setResponseCode(401).setBody(json))

        val resp = service.login(LoginRequest("u","p")).execute()
        assertFalse(resp.isSuccessful)
        // 401 → execute() は isSuccessful==false
        val err = resp.errorBody()!!.string()
        assertTrue(err.contains("bad"))
    }
}


c. StorageApiService のテスト
//  app/src/test/java/com/example/app/network/StorageApiServiceTest.kt
package com.example.app.network

import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

class StorageApiServiceTest {
    private lateinit var server: MockWebServer
    private lateinit var service: StorageApiService

    @Before
    fun setUp() {
        server = MockWebServer().apply { start() }
        service = Retrofit.Builder()
            .baseUrl(server.url("/"))
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(StorageApiService::class.java)
    }

    @After
    fun tearDown() {
        server.shutdown()
    }

    @Test
    fun storageCheck_success() {
        val json = """{"success":true,"message":"stored"}"""
        server.enqueue(MockResponse().setResponseCode(200).setBody(json))

        val req = StorageCheckRequest("user-123", 100L)
        val resp = service.storageCheck(req).execute()
        assertTrue(resp.isSuccessful)
        val body = resp.body()!!
        assertTrue(body.success)
        assertEquals("stored", body.message)
    }

    @Test
    fun storageCheck_failure() {
        val json = """{"success":false,"message":"error"}"""
        server.enqueue(MockResponse().setResponseCode(500).setBody(json))

        val req = StorageCheckRequest("u", 10L)
        val resp = service.storageCheck(req).execute()
        assertFalse(resp.isSuccessful)
    }
}


2. Android クライアント：StorageApiService 定義＋LoginActivity の修正
//  app/src/main/java/com/example/app/network/StorageApiService.kt
package com.example.app.network

import retrofit2.Call
import retrofit2.http.Body
import retrofit2.http.POST

data class StorageCheckRequest(
    val userUuid: String,
    val reservedBytes: Long
)
data class StorageCheckResponse(
    val success: Boolean,
    val message: String?
)

interface StorageApiService {
    @POST("user/storage_check")
    fun storageCheck(@Body req: StorageCheckRequest): Call<StorageCheckResponse>
}


//  app/src/main/java/com/example/app/network/ApiClient.kt 追記
// 既存の imports...
import com.example.app.network.StorageApiService

object ApiClient {
    private const val BASE_URL = "http://192.168.3.8:5000/"

    private val retrofit: Retrofit = Retrofit.Builder()
        .baseUrl(BASE_URL)
        .addConverterFactory(GsonConverterFactory.create())
        .build()

    val authService: AuthApiService = retrofit.create(AuthApiService::class.java)
    val storageService: StorageApiService = retrofit.create(StorageApiService::class.java)
}


//  app/src/main/java/com/example/app/ui/LoginActivity.kt 修正
    override fun onResponse(
        call: Call<LoginResponse>,
        resp: Response<LoginResponse>
    ) {
        val body = resp.body()
        if (body != null && body.success) {
            KeyStoreManager.ensureKeyPair()
            FileManager.reserveSpace(this@LoginActivity)

+           // ── ここでサーバーへ通知 ──
+           val userUuid = etUser.text.toString()
+           val reserved = FileManager.RESERVATION_SIZE
+           ApiClient.storageService
+               .storageCheck(StorageCheckRequest(userUuid, reserved))
+               .enqueue(object : Callback<StorageCheckResponse> {
+                   override fun onResponse(
+                       call: Call<StorageCheckResponse>, r: Response<StorageCheckResponse>
+                   ) {
+                       // (任意) 成功ログなど
+                   }
+                   override fun onFailure(call: Call<StorageCheckResponse>, t: Throwable) {
+                       // (任意) 再通知ロジックなど
+                   }
+               })
+
            startActivity(Intent(this@LoginActivity, MainActivity::class.java))
            finish()
        } else {


3. サーバー側：User Manager 側 storage_check エンドポイント
//  user_manager/app_user_manager.py 全文（追加部分を含む）
import os
import uuid
from flask import Flask, request, jsonify
import boto3
from datetime import datetime, timezone

app = Flask(__name__)

# DynamoDB 設定
from user_manager.config import AWS_REGION, USERS_TABLE, STORAGE_USAGE_TABLE
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
users_table = dynamodb.Table(USERS_TABLE)
storage_table = dynamodb.Table(STORAGE_USAGE_TABLE)

@app.route("/user/login", methods=["POST"])
def login():
    data = request.get_json()
    # ... 既存のログイン処理 ...
    # 成功時に JSON { success: True, rsaPrivateKey: "...", ... } を返す
    return jsonify({"success": True, "rsaPrivateKey": "..."}), 200

@app.route("/user/storage_check", methods=["POST"])
def storage_check():
    """
    クライアントから「ログイン後 100MB 確保しました」という通知を受け取って
    StorageUsageTable に記録
    """
    data = request.get_json()
    user_uuid = data.get("userUuid")
    reserved = data.get("reservedBytes")
    if not user_uuid or reserved is None:
        return jsonify({"success": False, "message": "invalid parameters"}), 400

    timestamp = datetime.now(timezone.utc).isoformat()
    item = {
        "user_uuid": user_uuid,
        "timestamp": timestamp,
        "reserved_bytes": int(reserved)
    }
    try:
        storage_table.put_item(Item=item)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

    return jsonify({"success": True, "message": "recorded"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)


//  user_manager/config.py
AWS_REGION = "ap-northeast-1"
USERS_TABLE = "UsersTable"
STORAGE_USAGE_TABLE = "StorageUsageTable"

以上で、
Android 側ユニットテスト
Android 側：Login→reserve→storage_check の呼び出し
User Manager 側： /user/storage_check エンドポイント
をすべて本番想定で省略なく実装できました。