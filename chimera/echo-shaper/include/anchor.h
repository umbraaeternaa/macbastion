/* anchor — ECHO's pf-anchor lifecycle (§8 Amendment A1, EP-2/EP-3). Loads/removes the
 * dummynet pf anchor that routes outbound traffic through CHIMERA's rate-limited pipe. The pf
 * actions run through an INJECTABLE backend so the lifecycle + fail-OPEN logic are tested
 * root-free; the real backend (write file + posix_spawn pfctl/dnctl) needs root and runs only
 * with per-command operator approval. The anchor RULE itself is a CANDIDATE pending validation
 * against live pf (the next, root slice). */
#ifndef SHAPER_ANCHOR_H
#define SHAPER_ANCHOR_H

#include <stddef.h>

#define SHAPER_ANCHOR_NAME "com.chimera.echo"
#define SHAPER_ANCHOR_PATH "/etc/pf.anchors/com.chimera.echo"

/* Write the pf-anchor file content (routes outbound through CHIMERA's dummynet pipe) into buf.
 * Returns 0 on success, -1 if buf is NULL or too small. CANDIDATE rule — pending live-pf
 * validation. Pure (no I/O). */
int shaper_anchor_build_rules(char *buf, size_t bufsz);

/* Injectable backend so tests record without root/pf. A NULL ops (or after a reset) restores
 * the real default (write file / posix_spawn pfctl+dnctl / unlink). */
typedef struct {
    int (*write_file)(const char *path, const char *content);
    int (*run)(const char *const argv[]); /* NULL-terminated argv; returns 0 on success */
    int (*remove_file)(const char *path);
} shaper_anchor_ops_t;
void shaper_anchor_set_ops(const shaper_anchor_ops_t *ops);

/* Load ECHO's pf anchor at rate_kbps: write the anchor file, configure the dummynet pipe
 * bandwidth, then load the anchor. Returns 0 only if every step succeeds; -1 on a bad rate or
 * any failed step. Needs root in production (the real backend). */
int shaper_anchor_apply(int rate_kbps);

/* Remove ECHO's pf anchor — FAIL-OPEN (EP-3): flush the anchor, delete the pipe, remove the
 * file, each best-effort so the network is ALWAYS restored even if a step fails. Returns 0. */
int shaper_anchor_clear(void);

#endif /* SHAPER_ANCHOR_H */
