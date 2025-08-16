// File: app/src/main/java/com/example/test100mb/util/Hex.kt
package com.example.test100mb.util

fun String.hexToBytes(): ByteArray =
    chunked(2).map { it.toInt(16).toByte() }.toByteArray()
