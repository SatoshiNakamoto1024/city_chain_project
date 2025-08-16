// app/src/main/java/com/example/test100mb/pqc/DilithiumNativeSigner.kt
package com.example.test100mb.pqc

object DilithiumNativeSigner {
    init { System.loadLibrary("pqc_native") }
    private external fun nativeSign(msg: ByteArray, sk: ByteArray): ByteArray

    fun sign(msg: ByteArray, secretKey: ByteArray): ByteArray = nativeSign(msg, secretKey)
}
