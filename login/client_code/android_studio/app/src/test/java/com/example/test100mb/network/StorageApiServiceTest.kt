package com.example.test100mb.network

// app/src/androidTest/java/com/example/test100mb/network/StorageApiServiceTest.kt

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
