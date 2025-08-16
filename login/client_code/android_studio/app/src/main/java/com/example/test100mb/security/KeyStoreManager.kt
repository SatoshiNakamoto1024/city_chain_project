package com.example.test100mb.security

//  app/src/main/java/com/example/test100mb/security/KeyStoreManager.kt

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import java.security.KeyPairGenerator
import java.security.KeyStore
import android.util.Base64

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
        val b64 = Base64.encodeToString(pkcs8, Base64.DEFAULT)
        return "-----BEGIN PRIVATE KEY-----\n$b64-----END PRIVATE KEY-----"
    }
}
