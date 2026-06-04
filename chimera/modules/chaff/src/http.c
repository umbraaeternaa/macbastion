/* http — libcurl GET wrapper (§5.1). The only outbound-network module. */
#include "http.h"

#include <curl/curl.h>

void http_global_init(void) { curl_global_init(CURL_GLOBAL_DEFAULT); }
void http_global_cleanup(void) { curl_global_cleanup(); }

/* Discard the response body — we only care that the request completed. */
static size_t discard(char *ptr, size_t size, size_t nmemb, void *userdata) {
    (void)ptr;
    (void)userdata;
    return size * nmemb;
}

chaff_result_t http_get(const char *url, long timeout_s) {
    if (!url) {
        return CHAFF_ERR;
    }
    CURL *curl = curl_easy_init();
    if (!curl) {
        return CHAFF_ERR_IO;
    }
    curl_easy_setopt(curl, CURLOPT_URL, url);
    curl_easy_setopt(curl, CURLOPT_NOSIGNAL, 1L); /* CRITICAL: no SIGPIPE/SIGALRM in threads */
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, timeout_s);
    curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, discard);

    chaff_result_t res = CHAFF_ERR_IO;
    if (curl_easy_perform(curl) == CURLE_OK) {
        long code = 0;
        curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &code);
        if (code >= 200 && code < 400) {
            res = CHAFF_OK;
        }
    }
    curl_easy_cleanup(curl);
    return res;
}
