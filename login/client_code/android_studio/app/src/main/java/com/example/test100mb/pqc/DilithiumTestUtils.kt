// File: app/src/main/java/com/example/test100mb/pqc/DilithiumTestUtils.kt
package com.example.test100mb.pqc

import org.bouncycastle.asn1.ASN1ObjectIdentifier
import org.bouncycastle.asn1.DERNull
import org.bouncycastle.asn1.DEROctetString
import org.bouncycastle.asn1.pkcs.PrivateKeyInfo
import java.io.File
import android.util.Base64
import kotlin.random.Random

object DilithiumTestUtils {

    /** Dilithium2 の OID（draft-ietf-pq-cose） */
    private val DILITHIUM2_OID = ASN1ObjectIdentifier("1.3.6.1.4.1.2.267.7.4.4")

    /**
     * ランダム 2544 byte を Dilithium2 の PKCS#8 に包んで PEM 保存
     */
    fun generateDummyPkcs8(dst: File) {
        val raw = Random.nextBytes(2544)          // ← サイズは適当
        val pkInfo = PrivateKeyInfo(
            /* algorithm */ org.bouncycastle.asn1.x509.AlgorithmIdentifier(
                DILITHIUM2_OID, DERNull.INSTANCE
            ),
            /* privateKey */ DEROctetString(raw)
        )
        val der = pkInfo.encoded
        val pemBody = Base64.encodeToString(der, Base64.NO_WRAP)
            .chunked(64).joinToString("\n")

        dst.writeText(
            "-----BEGIN PRIVATE KEY-----\n$pemBody\n-----END PRIVATE KEY-----\n"
        )
    }
}
