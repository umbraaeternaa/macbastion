/* attest — verify a connected peer IS the signed core via its audit-token code signature
 * (Slice 2b-ii). LOCAL_PEERTOKEN yields the peer's audit token, snapshotted by the kernel at
 * connect() and unforgeable by an unprivileged process; SecCode then checks that token's code
 * against core's designated requirement. Fail-closed: any NULL / error / non-match -> 0. */
#include "attest.h"

#include <mach/message.h> /* audit_token_t */
#include <sys/socket.h>
#include <sys/un.h> /* SOL_LOCAL, LOCAL_PEERTOKEN */

#include <CoreFoundation/CoreFoundation.h>
#include <Security/Security.h>

int attest_peer_is_core(int fd, const char *requirement) {
    if (requirement == NULL) {
        return 0;
    }

    audit_token_t token;
    socklen_t len = sizeof(token);
    if (getsockopt(fd, SOL_LOCAL, LOCAL_PEERTOKEN, &token, &len) != 0 || len != sizeof(token)) {
        return 0;
    }

    int ok = 0;
    CFDataRef token_data = CFDataCreate(NULL, (const UInt8 *)&token, sizeof(token));
    CFStringRef req_str = CFStringCreateWithCString(NULL, requirement, kCFStringEncodingUTF8);
    if (token_data != NULL && req_str != NULL) {
        const void *keys[] = {kSecGuestAttributeAudit};
        const void *vals[] = {token_data};
        CFDictionaryRef attrs = CFDictionaryCreate(
            NULL, keys, vals, 1, &kCFTypeDictionaryKeyCallBacks, &kCFTypeDictionaryValueCallBacks);
        SecCodeRef code = NULL;
        SecRequirementRef req = NULL;
        if (attrs != NULL
            && SecCodeCopyGuestWithAttributes(NULL, attrs, kSecCSDefaultFlags, &code) == errSecSuccess
            && SecRequirementCreateWithString(req_str, kSecCSDefaultFlags, &req) == errSecSuccess) {
            ok = (SecCodeCheckValidity(code, kSecCSDefaultFlags, req) == errSecSuccess) ? 1 : 0;
        }
        if (code != NULL) {
            CFRelease(code);
        }
        if (req != NULL) {
            CFRelease(req);
        }
        if (attrs != NULL) {
            CFRelease(attrs);
        }
    }
    if (token_data != NULL) {
        CFRelease(token_data);
    }
    if (req_str != NULL) {
        CFRelease(req_str);
    }
    return ok;
}
