/* statefiles — registry of CHIMERA's OWN state files to remove on PURGE tier0 (§3, §5.8).
 * tier0 kills the crown jewels first: CHIMERA's Keychain items (a separate half) and its
 * state DBs/files (this registry). purge_statefile_remove_all() unlink()s every registered
 * path. Paths must be ABSOLUTE and are copied in — CHIMERA registers ONLY its own files.
 * This deletes FILES ON DISK (unlike tier3's RAM-only wipe), so it is armed-gated and tested
 * on throwaway data only. The table is fixed-capacity — no allocation on the purge path. */
#ifndef PURGE_STATEFILES_H
#define PURGE_STATEFILES_H

#include <stddef.h>

#define PURGE_STATEFILE_MAX     32
#define PURGE_STATEFILE_PATHMAX 1024

/* Register an ABSOLUTE file path to remove on purge. The path is copied in. Returns 0 on
 * success; -1 if path is NULL/empty/not absolute/too long, or the registry is full. */
int purge_statefile_register(const char *path);

/* unlink() every registered path (the real tier0 file-removal action). Best-effort: a path
 * already gone is not an error. Returns 0. */
int purge_statefile_remove_all(void);

/* Number of currently registered paths. */
size_t purge_statefile_count(void);

/* Forget all registrations WITHOUT deleting (re-init / test teardown). */
void purge_statefile_reset(void);

#endif /* PURGE_STATEFILES_H */
