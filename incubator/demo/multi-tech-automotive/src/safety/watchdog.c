#include <stdint.h>

// traces: REQ-SAFE-002
// Safety-critical file in the combined automotive demo: exercises
// stacks/embedded-c's misra + safety-critical rules.
uint8_t watchdog_check(uint32_t elapsed_ms, uint32_t limit_ms) {
    uint8_t timed_out = 0U;
    if (elapsed_ms > limit_ms) {
        timed_out = 1U;
    }
    return timed_out;
}
