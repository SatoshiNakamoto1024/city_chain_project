// app/build.gradle.kts
plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
}

android {
    namespace = "com.example.test100mb"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.example.test100mb"
        minSdk = 24
        targetSdk = 35
        versionCode = 1
        versionName = "1.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        // 追加：使用する ABI を宣言
        externalNativeBuild {
            cmake {
                cppFlags += ""
                abiFilters += listOf("arm64-v8a", "x86_64")
            }
        }
    }

    externalNativeBuild {
        cmake {
            path = file("src/main/cpp/CMakeLists.txt") // ←絶対にここに合わせる
        }
    }

    buildTypes {
        release {
            // ← ProGuard を使う場合はルールを追加
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
    kotlinOptions { jvmTarget = "11" }
    buildFeatures { compose = true }
}

dependencies {
    /* ---------- UI / Compose ---------- */
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.activity.compose)
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.ui)
    implementation(libs.androidx.ui.graphics)
    implementation(libs.androidx.ui.tooling.preview)
    implementation(libs.androidx.material3)

    /* ---------- ネットワーク ---------- */
    implementation("com.squareup.retrofit2:retrofit:2.9.0")
    implementation("com.squareup.retrofit2:converter-gson:2.9.0")
    implementation("com.squareup.okio:okio:3.7.0")   // v3 系
    implementation("androidx.appcompat:appcompat:1.6.1")

    /* ---------- Bouncy Castle (PQC 対応 & Android 互換) ---------- */
    // ① PQC を含む “ext” パッケージ
    implementation("org.bouncycastle:bcprov-ext-jdk15to18:1.78.1")  // ← NEW
    // ② X.509 / PKCS 高水準 API
    implementation("org.bouncycastle:bcpkix-jdk15to18:1.78.1")      // ← NEW

    /* ---- (任意) FIPS ----
       FIPS 対応が本当に必要な場合だけ有効化。
       FIPS と通常プロバイダは同時ロードできないので注意。
    */
    // implementation("org.bouncycastle:bc-fips:1.0.2")  // Java 8 byte-code なので Android OK :contentReference[oaicite:3]{index=3}

    /* ---------- テスト ---------- */
    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test.ext:junit:1.1.5")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.5.1")
}

/* ---- 古い jdk15on 系を “万が一” 引き込まれた場合に備えて除外 ---- */
configurations.all {
    exclude(group = "org.bouncycastle", module = "bcprov-jdk15on")
    exclude(group = "org.bouncycastle", module = "bcpkix-jdk15on")
    exclude(group = "org.bouncycastle", module = "bcprov-ext-jdk15on")
    exclude(group = "org.bouncycastle", module = "bcpqc-jdk15on")
}
