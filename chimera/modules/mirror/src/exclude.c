/* exclude — RED-B stub. Match always misses, mutations always error, so the
 * list tests fail honestly. Real fixed-capacity list logic lands in GREEN. */
#include "exclude.h"

bool exclude_match(const exclusion_list_t *list, const char *bundle_id) {
    (void)list;
    (void)bundle_id;
    return false; /* stub: nothing is ever excluded */
}

mirror_result_t exclude_add(exclusion_list_t *list, const char *bundle_id) {
    (void)list;
    (void)bundle_id;
    return MIRROR_ERR; /* stub */
}

mirror_result_t exclude_remove(exclusion_list_t *list, const char *bundle_id) {
    (void)list;
    (void)bundle_id;
    return MIRROR_ERR; /* stub */
}
