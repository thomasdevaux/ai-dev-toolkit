#include <stdint.h>

/* Dummy non-safety embedded C file: misra-rules should apply here,
 * safety-critical-rules should not (this file is outside src/safety/). */
int32_t add(int32_t a, int32_t b) {
    return a + b;
}
