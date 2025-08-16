// app/src/main/cpp/dilithium_signer.c
#include <jni.h>
#include <stdint.h>
#include <string.h>

// ★★ 実装を簡略化：ここでは「署名しないで元データを返すだけ」
//    → まずアプリがクラッシュしない状態を作り、後で真の Dilithium 実装と差し替える
JNIEXPORT jbyteArray JNICALL
Java_com_example_test100mb_pqc_DilithiumNativeSigner_nativeSign(
        JNIEnv* env, jobject _this,
        jbyteArray msg_, jbyteArray sk_)
{
    // 呼び出し引数を取得
    jsize msg_len = (*env)->GetArrayLength(env, msg_);
    jbyte* msg    = (*env)->GetByteArrayElements(env, msg_, NULL);

    // ここで本来は Dilithium 署名を生成する
    // ----  ダミー：元メッセージをそのまま返す  ----
    jbyteArray out = (*env)->NewByteArray(env, msg_len);
    (*env)->SetByteArrayRegion(env, out, 0, msg_len, msg);

    (*env)->ReleaseByteArrayElements(env, msg_, msg, 0);
    return out;
}