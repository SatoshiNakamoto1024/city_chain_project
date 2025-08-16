// File: client_code/game_check.c
/*
  Linux系のゲーム機 (Raspberry Piベースや独自Linuxベース) を想定したサンプル。
  /data や / といったパスの空き容量を statvfs で取得し、libcurl でサーバーへPOST。
*/

#include <stdio.h>
#include <sys/statvfs.h>
#include <curl/curl.h>

#define SERVER_URL "http://your-server-ip:5050/login"
#define USERNAME "admin"
#define PASSWORD "password"

long long get_free_space(const char* path) {
    struct statvfs st;
    if (statvfs(path, &st) != 0) {
        return -1;
    }
    return (long long)st.f_bavail * st.f_frsize;
}

int main(int argc, char* argv[]) {
    const char* path = "/data";  // ゲーム機の内部領域
    long long free_bytes = get_free_space(path);

    printf("Free space at %s: %lld bytes\n", path, free_bytes);

    // libcurl で POST
    CURL *curl;
    CURLcode res;
    curl = curl_easy_init();
    if (!curl) {
        fprintf(stderr, "Failed to init curl\n");
        return 1;
    }

    // JSON ボディ
    char json[256];
    snprintf(json, sizeof(json),
        "{\"username\":\"%s\",\"password\":\"%s\",\"client_free_space\":%lld}",
        USERNAME, PASSWORD, free_bytes
    );

    struct curl_slist *headers = NULL;
    headers = curl_slist_append(headers, "Content-Type: application/json");
    // User-Agent で "game" と判定してもらうために
    headers = curl_slist_append(headers, "User-Agent: Mozilla/5.0 (PlayStation 5.0)");

    curl_easy_setopt(curl, CURLOPT_URL, SERVER_URL);
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, json);

    res = curl_easy_perform(curl);
    if (res != CURLE_OK) {
        fprintf(stderr, "curl_easy_perform() failed: %s\n", curl_easy_strerror(res));
    }

    curl_slist_free_all(headers);
    curl_easy_cleanup(curl);

    return (res == CURLE_OK) ? 0 : 1;
}
