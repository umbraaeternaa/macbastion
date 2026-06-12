// CHIMERA PURGE — AArch64 secure-wipe primitives (§5.8 RAM erase, dc zva).
//
//   size_t purge_zva_blocksize(void) : DC ZVA block size in bytes, or 0 if `dc zva` is
//                                      prohibited at this exception level (DCZID_EL0.DZP).
//   void   purge_zva_one(void *block): zero one block at x0 via `dc zva`.
//
// macOS/AArch64: exported C symbols carry a leading underscore.

.text

.global _purge_zva_blocksize
.p2align 2
_purge_zva_blocksize:
    mrs     x1, dczid_el0       // [3:0]=BS (log2 words per block), [4]=DZP (prohibited)
    tbnz    x1, #4, 1f          // DZP set -> dc zva not allowed -> return 0
    and     x1, x1, #0xf        // x1 = BS
    mov     x0, #4              // 4 bytes per word
    lsl     x0, x0, x1          // bytes = 4 << BS
    ret
1:
    mov     x0, #0
    ret

.global _purge_zva_one
.p2align 2
_purge_zva_one:
    dc      zva, x0             // zero the block containing x0 (x0 must be block-aligned)
    ret
