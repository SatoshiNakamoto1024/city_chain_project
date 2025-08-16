package com.example.test100mb.network

// app/src/androidTest/java/com/example/test100mb/network/AuthApiServiceTest.kt

import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

class AuthApiServiceTest {
    private lateinit var server: MockWebServer
    private lateinit var service: AuthApiService

    @Before
    fun setUp() {
        server = MockWebServer().apply { start() }
        service = Retrofit.Builder()
            .baseUrl(server.url("/"))
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(AuthApiService::class.java)
    }

    @After
    fun tearDown() {
        server.shutdown()
    }

    @Test
    fun login_success() {
        val json = """
          {
            "success": true,
            "rsaPrivateKey": "BASE64_PEM",
            "message": "OK"
          }
        """
        server.enqueue(MockResponse().setResponseCode(200).setBody(json))

        val resp = service.login(LoginRequest("u","p")).execute()
        assertTrue(resp.isSuccessful)
        val body = resp.body()!!
        assertTrue(body.success)
        assertEquals("BASE64_PEM", body.rsaPrivateKey)
    }

    @Test
    fun login_failure() {
        val json = """{"success":false,"message":"bad"}"""
        server.enqueue(MockResponse().setResponseCode(401).setBody(json))

        val resp = service.login(LoginRequest("u","p")).execute()
        assertFalse(resp.isSuccessful)
        // 401 → execute() は isSuccessful==false
        val err = resp.errorBody()!!.string()
        assertTrue(err.contains("bad"))
    }
}
