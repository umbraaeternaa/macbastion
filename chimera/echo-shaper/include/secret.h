/* secret — per-boot shared secret for the shaper's privileged channel (§8 Amendment A1, EP-5,
 * mirrors the shim SS-3/SS-4). 32 CSPRNG bytes, hex-encoded, held ONLY in memory (zero disk).
 * The dispatch already gates the pf ops on it; the daemon (main.c) generates it at start and the
 * handoff to the attested core is a later sub-slice. */
#ifndef SHAPER_SECRET_H
#define SHAPER_SECRET_H

#define SHAPER_SECRET_HEX_LEN 64 /* 32 bytes, hex-encoded */

/* Fill out (caller provides >= SHAPER_SECRET_HEX_LEN+1 bytes) with a fresh hex per-boot secret. */
void shaper_secret_generate(char *out);

/* Constant-time equality of two SHAPER_SECRET_HEX_LEN-char hex secrets. 1 = equal, 0 = differ. */
int shaper_secret_equal(const char *a, const char *b);

#endif /* SHAPER_SECRET_H */
