/*
 * mac_spoof.c — generate random MAC, apply via raw ioctl(SIOCSIFLLADDR)
 *
 * Entropy source: getentropy(2) — kernel-backed CSPRNG, ultimately
 *   seeded by the same Apple Silicon hardware RNG as RNDR. RNDR itself
 *   is privileged (EL1+) on macOS, so user-space reads must go via the
 *   syscall path.
 *
 * Why C at all (vs `ifconfig ether`):
 *   - direct ioctl, no shell-out, no parsing
 *   - clean exit codes for orchestration from Python (macbastion CLI)
 *   - first step toward more privileged native modules (kqwatch, secwipe)
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <unistd.h>
#include <errno.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <sys/random.h>
#include <net/if.h>
#include <net/if_dl.h>
#include <netinet/in.h>
#include <ifaddrs.h>

// Generate a 6-byte locally-administered, unicast MAC into `out`.
static int gen_random_mac(uint8_t out[6]) {
    if (getentropy(out, 6) != 0) {
        perror("getentropy");
        return -1;
    }
    // First octet: set locally-administered bit (0x02), clear multicast (0x01)
    out[0] = (out[0] | 0x02) & 0xFE;
    return 0;
}

static void print_mac(const uint8_t mac[6]) {
    printf("%02x:%02x:%02x:%02x:%02x:%02x\n",
           mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
}

static int cmd_show(const char *iface) {
    struct ifaddrs *ifap, *p;
    if (getifaddrs(&ifap) != 0) { perror("getifaddrs"); return 1; }
    int found = 0;
    for (p = ifap; p != NULL; p = p->ifa_next) {
        if (!p->ifa_addr || p->ifa_addr->sa_family != AF_LINK) continue;
        if (strcmp(p->ifa_name, iface) != 0) continue;
        struct sockaddr_dl *sdl = (struct sockaddr_dl *)p->ifa_addr;
        if (sdl->sdl_alen == 6) {
            printf("%s: ", iface);
            print_mac((uint8_t *)LLADDR(sdl));
            found = 1;
            break;
        }
    }
    freeifaddrs(ifap);
    if (!found) {
        fprintf(stderr, "interface '%s' not found or has no MAC\n", iface);
        return 2;
    }
    return 0;
}

static int cmd_set(const char *iface, const uint8_t mac[6]) {
    int s = socket(AF_INET, SOCK_DGRAM, 0);
    if (s < 0) { perror("socket"); return 1; }

    struct ifreq ifr;
    memset(&ifr, 0, sizeof(ifr));
    strncpy(ifr.ifr_name, iface, IFNAMSIZ - 1);
    ifr.ifr_addr.sa_len    = 6;
    ifr.ifr_addr.sa_family = AF_LINK;
    memcpy(ifr.ifr_addr.sa_data, mac, 6);

    if (ioctl(s, SIOCSIFLLADDR, &ifr) < 0) {
        perror("ioctl(SIOCSIFLLADDR)");
        fprintf(stderr,
                "hint: needs root; on macOS Wi-Fi (en0) interface must be\n"
                "      disassociated first. Use the stealth wrapper script.\n");
        close(s);
        return 3;
    }
    close(s);
    printf("OK: %s now ", iface);
    print_mac(mac);
    return 0;
}

static void usage(const char *p) {
    fprintf(stderr,
        "Usage:\n"
        "  %s gen              — generate random MAC, print only\n"
        "  %s show <iface>     — show current MAC of interface\n"
        "  %s set  <iface>     — generate + apply (needs root)\n",
        p, p, p);
}

int main(int argc, char **argv) {
    if (argc < 2) { usage(argv[0]); return 1; }

    if (strcmp(argv[1], "gen") == 0) {
        uint8_t mac[6];
        if (gen_random_mac(mac) != 0) return 1;
        print_mac(mac);
        return 0;
    }
    if (strcmp(argv[1], "show") == 0 && argc == 3) return cmd_show(argv[2]);
    if (strcmp(argv[1], "set")  == 0 && argc == 3) {
        uint8_t mac[6];
        if (gen_random_mac(mac) != 0) return 1;
        return cmd_set(argv[2], mac);
    }
    usage(argv[0]);
    return 1;
}
