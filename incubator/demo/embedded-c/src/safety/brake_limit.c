#include <stdint.h>

// traces: REQ-SAFE-001
// Dummy safety-critical file: both misra-rules and safety-critical-rules
// should apply here (path matches src/safety/**).
uint8_t clamp_brake_pressure(uint8_t requested_percent) {
    uint8_t result = requested_percent;
    if (result > 100U) {
        result = 100U;
    }
    return result;
}
