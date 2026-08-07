#include <stdint.h>

/* Dummy stand-in for Simulink-generated C, matching model/brake_controller.slx.
 * Used to validate the generate-code-review skill (cross-checks generated
 * code against the model rather than just C style). */
uint8_t brake_controller_step(uint8_t requested_percent) {
    return requested_percent;
}
