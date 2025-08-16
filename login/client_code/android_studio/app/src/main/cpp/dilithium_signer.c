// app/src/main/cpp/dilithium_signer.c

#include <jni.h>
#include <stdlib.h>
#include <android/log.h>
#include <string.h>

#define LOG_TAG "pqc_native"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO,  LOG_TAG, __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, LOG_TAG, __VA_ARGS__)

// JNIEXPORT/JNICALL マクロだけで C 版シンボルを定義
JNIEXPORT jbyteArray JNICALL
Java_com_example_test100mb_pqc_DilithiumSigner_00024DilithiumNative_sign(
        JNIEnv *env,
        jclass /* clazz */,
        jbyteArray jmsg,
        jbyteArray /* jsk */
) {
    jsize len = (*env)->GetArrayLength(env, jmsg);
    jbyte* buf = (*env)->GetByteArrayElements(env, jmsg, NULL);
    if (!buf) {
        LOGE("GetByteArrayElements failed");
        return NULL;
    }
    jbyteArray out = (*env)->NewByteArray(env, len);
    (*env)->SetByteArrayRegion(env, out, 0, len, buf);
    (*env)->ReleaseByteArrayElements(env, jmsg, buf, JNI_ABORT);
    LOGI("dummy sign called, len=%d", len);
    return out;
}