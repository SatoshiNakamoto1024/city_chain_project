#ifndef DILITHIUM_SIGNER_H
#define DILITHIUM_SIGNER_H

#include <jni.h>

#ifdef __cplusplus
extern "C" {
#endif

// JNI で Java → C に呼び出すための関数
JNIEXPORT jbyteArray JNICALL
Java_com_example_test100mb_pqc_DilithiumNativeSigner_nativeSign(
        JNIEnv *env,
        jobject thiz,
        jbyteArray message,
        jbyteArray secret_key
);

#ifdef __cplusplus
}
#endif

#endif // DILITHIUM_SIGNER_H
