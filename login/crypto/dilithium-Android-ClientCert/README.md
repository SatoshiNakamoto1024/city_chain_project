❷ Rust → Android .so をビルド（cargo-ndk を使う）

# まだなら
cargo install cargo-ndk

まだターゲットが入っていない場合は、以下を最初に1回だけ実行してください：
rustup target add aarch64-linux-android armv7-linux-androideabi x86_64-linux-android

# プロジェクト直下 (dilithium-Android-ClientCert/) で
cargo ndk -t arm64-v8a -t armeabi-v7a -t x86_64 -o ../app/src/main/jniLibs build --release

これで
app/src/main/jniLibs/arm64-v8a/libdilithium5.so などが並びます

CMake も NDK-build も要りません – すでに .so が配置されたので
Android Gradle Plugin が自動でパッケージします


どう配置すればいい？ ― 結論だけ先に
やること	必須 / 任意	詳細
① app/src/main/jniLibs/<abi>/libdilithium_android_clientcert.so を置く	必須	先ほど cargo-ndk が吐いた .so を 3 ABI 分コピーする
② Kotlin の System.loadLibrary("dilithium_android_clientcert") を追記	必須	既存の loadLibrary("pqc_native") が残っていても OK
③ 既存の libpqc_native.so を残すか？	任意	- 他で still 使っていれば残す
- 使っていないなら削除しても可

手順（1 回だけで完了）
Rust ビルド成果物をコピー
crypto/dilithium-Android-ClientCert/target/aarch64-linux-android/release/libdilithium_Android_ClientCert.so
└─► app/src/main/jniLibs/arm64-v8a/

crypto/dilithium-Android-ClientCert/target/armv7-linux-androideabi/release/libdilithium_Android_ClientCert.so
└─► app/src/main/jniLibs/armeabi-v7a/

crypto/dilithium-Android-ClientCert/target/x86_64-linux-android/release/libdilithium_Android_ClientCert.so
└─► app/src/main/jniLibs/x86_64/
すでに cargo ndk -o ../app/src/main/jniLibs … で指定していれば自動で入っています。

Kotlin 側ロード行を追加
// どこかアプリ起動時に 1 度だけ
System.loadLibrary("dilithium_Android_ClientCert")   // ← 新 .so
System.loadLibrary("pqc_native")                     // ← 既存が必要ならそのまま
不要なら libpqc_native.so を削除

DilithiumSigner だけで JNI を呼ぶなら削除して OK

他クラス（NTRU など）が pqc_native にまだ依存している場合は残す

ビルド & テスト
./gradlew clean assembleDebug
./gradlew connectedAndroidTest      # ← InstrumentationTest が通るか確認

なぜこれで良いの？
今回コンパイルした .so に含まれる JNI シンボルは
Java_com_example_test100mb_pqc_DilithiumSigner_00024DilithiumNative_sign
だけ。
– 既存の libpqc_native.so とシンボル衝突しません。

Android は ライブラリ名単位 でロード管理するため、
dilithium_android_clientcert を別名で置けば共存可能。

Kotlin 側で 必要な .so だけ System.loadLibrary すれば
VM が該当シンボルを正しく解決します。