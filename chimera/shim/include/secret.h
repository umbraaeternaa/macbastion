/* Per-boot shared secret for the privileged channel (SS-3/SS-4). 32 CSPRNG bytes,
 * hex-encoded, held ONLY in memory (zero disk). Slice 2 gates the destructive ops on it;
 * the handoff to core (code-signature-verified) is a later sub-slice. */
#ifndef SHIM_SECRET_H
#define SHIM_SECRET_H

#define SHIM_SECRET_HEX_LEN 64 /* 32 bytes, hex-encoded */

/* Fill out (caller provides >= SHIM_SECRET_HEX_LEN+1 bytes) with a fresh hex-encoded
 * per-boot secret. */
void secret_generate(char *out);

/* Constant-time equality of two SHIM_SECRET_HEX_LEN-char hex secrets. 1 = equal, 0 = differ. */
int secret_equal(const char *a, const char *b);

#endif /* SHIM_SECRET_H */
