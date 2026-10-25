/**
 * CDPR Embedded Micro-ROS Client for ESP32.
 * FreeRTOS task coordinating micro-ROS DDS communication, deterministic FSM,
 * communication-loss watchdog, command validation, and fail-closed servo interface.
 *
 * Compliant with Master Task Specification & Safety Corrections:
 * - Dedicated UART2 transport on GPIO17 TX / GPIO16 RX @ 115200 baud
 * - USB serial console retained on UART0
 * - Real micro-ROS agent discovery & liveness monitoring via rmw_uros_ping_agent
 * - Lifecycle tracking with idempotent, leak-free entity initialization and teardown
 * - Fail-closed stop path engaged immediately upon Agent loss during motion
 * - 250 ms monotonic communication watchdog latching SAFE_STOP
 * - Reconnection strictly forbidden from auto-arming or enabling motion
 * - Thread-safe FSM operations guarded by FreeRTOS recursive mutex
 * - Fail-closed feedback formatting: unverified telemetry explicitly marked unavailable
 * - Torque hard-disabled in software; physical STO unverified
 */
#include <stdio.h>
#include <string.h>
#include <math.h>
#include <stdbool.h>
#include <stdatomic.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "driver/uart.h"

#include <rcl/rcl.h>
#include <rcl/error_handling.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>

#include <rmw_microxrcedds_c/config.h>
#include <rmw_microros/rmw_microros.h>
#include <rmw_microros/ping.h>
#include <rmw_microros/custom_transport.h>

#include <sensor_msgs/msg/joint_state.h>
#include <std_msgs/msg/int32.h>
#include <std_msgs/msg/bool.h>
#include <micro_ros_utilities/type_utilities.h>

#include "esp32_serial_transport.h"
#include "app_state.h"
#include "servo_driver_interface.h"
#include "cdpr_command_validator.h"
#include "cdpr_feedback_interface.h"

static const char* TAG = "CDPR_FIRMWARE";

#define WATCHDOG_TIMEOUT_MS              250
#define AGENT_PING_TIMEOUT_MS            100
#define AGENT_PING_ATTEMPTS              1
#define AGENT_DISCOVERY_INTERVAL_MS      1000
#define AGENT_LIVENESS_CHECK_INTERVAL_MS 2000
#define STATUS_PUBLISH_INTERVAL_MS       100

#ifndef CONFIG_MICRO_ROS_APP_STACK
#define CONFIG_MICRO_ROS_APP_STACK       16384
#endif

#ifndef CONFIG_MICRO_ROS_APP_TASK_PRIO
#define CONFIG_MICRO_ROS_APP_TASK_PRIO   5
#endif

/* Dedicated micro-ROS UART port: UART2 (TX=GPIO17, RX=GPIO16) */
static size_t g_microros_uart_port = UART_NUM_2;

/* Global state variables protected by g_fsm_mutex */
static cdpr_firmware_state_t  g_current_state = STATE_BOOT;
static cdpr_servo_status_t    g_servo_status;
static cdpr_command_tracker_t g_cmd_tracker;
static SemaphoreHandle_t      g_fsm_mutex = NULL;
static int64_t                g_last_valid_command_time_us = 0;
static bool                   g_agent_connected = false;
static bool                   g_reset_requested = false;
static bool                   g_watchdog_tripped = false;

/* Synchronization primitives for executor vs teardown concurrency */
#define EXECUTOR_TEARDOWN_TIMEOUT_MS     100
#define EXECUTOR_SPIN_TIMEOUT_MS         10

static SemaphoreHandle_t      g_executor_mutex = NULL;
static TaskHandle_t           g_executor_spinning_task = NULL;
static atomic_bool            g_teardown_in_progress = false;
static atomic_bool            g_cleanup_failed_latched = false;
static atomic_bool            g_disconnect_pending = false;

/* Entity initialization tracking for granular, leak-free cleanup */
typedef struct {
    bool support_init;
    bool node_init;
    bool cmd_sub_init;
    bool ctrl_sub_init;
    bool feedback_pub_init;
    bool status_pub_init;
    bool feedback_valid_pub_init;
    bool cmd_msg_memory;
    bool feedback_msg_memory;
    bool executor_init;
    bool cmd_sub_in_executor;
    bool ctrl_sub_in_executor;
    bool executor_spinning;
} cdpr_entity_lifecycle_t;

static cdpr_entity_lifecycle_t g_lifecycle = {0};

/**
 * Checks whether any micro-ROS entities remain unresolved/initialized.
 */
static inline bool cdpr_has_unresolved_entities(const cdpr_entity_lifecycle_t* lc) {
    if (!lc) return false;
    return (
        lc->support_init ||
        lc->node_init ||
        lc->cmd_sub_init ||
        lc->ctrl_sub_init ||
        lc->feedback_pub_init ||
        lc->status_pub_init ||
        lc->feedback_valid_pub_init ||
        lc->cmd_msg_memory ||
        lc->feedback_msg_memory ||
        lc->executor_init
    );
}

/**
 * Validates that all entities and dynamic memory buffers required for executor spinning
 * are cleanly initialized, intact, and not in a torn-down or partial state.
 */
static inline bool cdpr_is_lifecycle_ready_for_spin(const cdpr_entity_lifecycle_t* lc) {
    if (!lc) return false;
    return (
        lc->support_init &&
        lc->node_init &&
        lc->executor_init &&
        lc->cmd_sub_init &&
        lc->ctrl_sub_init &&
        lc->feedback_pub_init &&
        lc->status_pub_init &&
        lc->feedback_valid_pub_init &&
        lc->cmd_msg_memory &&
        lc->feedback_msg_memory
    );
}

/**
 * Returns true if the calling task is currently running the executor spin_some loop.
 * Used to prevent self-deadlock and use-after-free when teardown or disconnect is
 * initiated from within an executor callback.
 */
static inline bool cdpr_is_executor_spinning_on_current_task(void) {
    if (!g_lifecycle.executor_spinning) {
        return false;
    }
    return (g_executor_spinning_task != NULL &&
            g_executor_spinning_task == xTaskGetCurrentTaskHandle());
}

/**
 * Acquires executor mutex before spinning.
 * Fails closed if teardown is in progress, cleanup has failed/timed out, or
 * any lifecycle entity remains unresolved.
 * Bounded timeout ensures deterministic behavior without thread starvation.
 */
static bool cdpr_executor_acquire_for_spin(TickType_t timeout_ticks) {
    if (g_executor_mutex == NULL) return false;

    /* Fast-path pre-check: fail-closed if teardown active, cleanup failed, or uninitialized */
    if (atomic_load_explicit(&g_teardown_in_progress, memory_order_acquire) ||
        atomic_load_explicit(&g_cleanup_failed_latched, memory_order_acquire) ||
        !cdpr_is_lifecycle_ready_for_spin(&g_lifecycle)) {
        return false;
    }

    if (xSemaphoreTake(g_executor_mutex, timeout_ticks) != pdTRUE) {
        return false;
    }

    /* Re-verify all fail-closed conditions under g_executor_mutex protection */
    if (atomic_load_explicit(&g_teardown_in_progress, memory_order_acquire) ||
        atomic_load_explicit(&g_cleanup_failed_latched, memory_order_acquire) ||
        !cdpr_is_lifecycle_ready_for_spin(&g_lifecycle)) {
        xSemaphoreGive(g_executor_mutex);
        return false;
    }

    g_lifecycle.executor_spinning = true;
    g_executor_spinning_task = xTaskGetCurrentTaskHandle();
    return true;
}

/**
 * Releases executor mutex after spinning.
 * Unconditionally restores spinning state.
 */
static void cdpr_executor_release_from_spin(void) {
    g_lifecycle.executor_spinning = false;
    g_executor_spinning_task = NULL;
    if (g_executor_mutex != NULL) {
        xSemaphoreGive(g_executor_mutex);
    }
}

/* micro-ROS entities */
static rcl_allocator_t       g_allocator;
static rclc_support_t        g_support;
static rcl_node_t            g_node;
static rclc_executor_t       g_executor;
static rcl_subscription_t    g_cmd_sub;
static rcl_subscription_t    g_ctrl_sub;
static rcl_publisher_t       g_feedback_pub;
static rcl_publisher_t       g_status_pub;
static rcl_publisher_t       g_feedback_valid_pub;
static sensor_msgs__msg__JointState g_cmd_msg;
static std_msgs__msg__Int32         g_ctrl_msg;
static sensor_msgs__msg__JointState g_feedback_msg;
static std_msgs__msg__Int32         g_status_msg;
static std_msgs__msg__Bool          g_feedback_valid_msg;

/* Forward declarations */
static bool destroy_microros_entities(void);
static bool cdpr_recover_unresolved_lifecycle(void);
static bool fsm_transition_locked(cdpr_firmware_state_t new_state);
static bool fsm_transition_to(cdpr_firmware_state_t new_state);

/**
 * Internal transition logic executed while holding g_fsm_mutex.
 */
static bool fsm_transition_locked(cdpr_firmware_state_t new_state) {
    if (!cdpr_is_valid_transition(g_current_state, new_state)) {
        ESP_LOGE(TAG, "FORBIDDEN state transition: [%s] -> [%s]",
                 cdpr_state_to_str(g_current_state), cdpr_state_to_str(new_state));
        return false;
    }

    /* Safety gate: entering MOTION_ENABLED requires genuine verified hardware and permitted torque */
    if (new_state == STATE_MOTION_ENABLED) {
        if (!g_servo_status.is_hardware_verified || !g_servo_status.torque_permitted) {
            ESP_LOGE(TAG, "FORBIDDEN transition to MOTION_ENABLED: Hardware is UNVERIFIED (Fail-closed; torque remains software-disabled).");
            return false;
        }
        g_last_valid_command_time_us = esp_timer_get_time();
    }

    /* Safety gate: leaving SAFE_STOP to READY requires explicit operator reset and healthy conditions */
    if (g_current_state == STATE_SAFE_STOP && new_state == STATE_READY) {
        if (!g_reset_requested) {
            ESP_LOGE(TAG, "FORBIDDEN transition: SAFE_STOP is latched. Explicit operator reset (/cdpr/command/control=2) required.");
            return false;
        }
        if (!g_agent_connected) {
            ESP_LOGE(TAG, "FORBIDDEN transition: Cannot reset SAFE_STOP while Agent is disconnected.");
            return false;
        }
        if (g_servo_status.active_drive_faults != 0) {
            ESP_LOGE(TAG, "FORBIDDEN transition: Cannot reset SAFE_STOP with active drive faults (0x%08lx).",
                     (unsigned long)g_servo_status.active_drive_faults);
            return false;
        }
        g_reset_requested = false;
        g_watchdog_tripped = false;
    }

    ESP_LOGI(TAG, "State transition: [%s] -> [%s]",
             cdpr_state_to_str(g_current_state), cdpr_state_to_str(new_state));
    g_current_state = new_state;

    if (new_state == STATE_SAFE_STOP || new_state == STATE_FAULT) {
        cdpr_servo_emergency_safe_stop(&g_servo_status);
    }

    return true;
}

/**
 * Public thread-safe state transition function.
 */
static bool fsm_transition_to(cdpr_firmware_state_t new_state) {
    if (g_fsm_mutex == NULL) return false;
    if (xSemaphoreTakeRecursive(g_fsm_mutex, pdMS_TO_TICKS(50)) != pdTRUE) {
        ESP_LOGE(TAG, "Failed to acquire FSM mutex for state transition");
        return false;
    }

    bool res = fsm_transition_locked(new_state);
    xSemaphoreGiveRecursive(g_fsm_mutex);
    return res;
}

/**
 * Atomically reads current FSM state.
 */
static cdpr_firmware_state_t fsm_get_state(void) {
    if (g_fsm_mutex == NULL) return STATE_BOOT;
    xSemaphoreTakeRecursive(g_fsm_mutex, portMAX_DELAY);
    cdpr_firmware_state_t st = g_current_state;
    xSemaphoreGiveRecursive(g_fsm_mutex);
    return st;
}

/**
 * Atomically checks watchdog in MOTION_ENABLED. Latches SAFE_STOP if timeout occurs.
 */
static void fsm_check_watchdog(int64_t now_us) {
    if (g_fsm_mutex == NULL) return;
    if (xSemaphoreTakeRecursive(g_fsm_mutex, pdMS_TO_TICKS(10)) != pdTRUE) return;

    if (g_current_state == STATE_MOTION_ENABLED) {
        int64_t elapsed_ms = (now_us - g_last_valid_command_time_us) / 1000;
        if (elapsed_ms > WATCHDOG_TIMEOUT_MS) {
            ESP_LOGE(TAG, "WATCHDOG TIMEOUT: No valid command for %lld ms. Latching SAFE_STOP.", elapsed_ms);
            g_watchdog_tripped = true;
            (void)fsm_transition_locked(STATE_SAFE_STOP);
        }
    }
    xSemaphoreGiveRecursive(g_fsm_mutex);
}

/**
 * Handles Agent disconnection in a thread-safe manner.
 * Engages fail-closed stop path before entity teardown if moving.
 */
static void fsm_handle_agent_disconnect(void) {
    if (g_fsm_mutex == NULL) return;
    xSemaphoreTakeRecursive(g_fsm_mutex, portMAX_DELAY);

    g_agent_connected = false;

    if (g_current_state == STATE_MOTION_ENABLED) {
        ESP_LOGW(TAG, "Agent loss detected while MOTION_ENABLED: Engaging immediate SAFE_STOP.");
        cdpr_servo_emergency_safe_stop(&g_servo_status);
        (void)fsm_transition_locked(STATE_SAFE_STOP);
    }

    xSemaphoreGiveRecursive(g_fsm_mutex);

    /* If called from within an active executor callback on the executor task,
     * defer teardown until rclc_executor_spin_some() completes to avoid self-deadlock
     * and use-after-free of the executor while in its own callback. */
    if (cdpr_is_executor_spinning_on_current_task()) {
        ESP_LOGW(TAG, "Agent disconnect initiated from executor callback: Deferring entity teardown until spin completes.");
        atomic_store_explicit(&g_disconnect_pending, true, memory_order_release);
        return;
    }

    bool clean = destroy_microros_entities();

    xSemaphoreTakeRecursive(g_fsm_mutex, portMAX_DELAY);
    if (!clean) {
        ESP_LOGE(TAG, "Teardown had unresolved entities! Transitioning to STATE_FAULT (Fail-closed).");
        (void)fsm_transition_locked(STATE_FAULT);
    } else {
        (void)fsm_transition_locked(STATE_WAITING_FOR_AGENT);
    }
    xSemaphoreGiveRecursive(g_fsm_mutex);
}

/**
 * Atomically updates Agent connection status.
 */
static void fsm_set_agent_connected(bool connected) {
    if (g_fsm_mutex == NULL) return;
    xSemaphoreTakeRecursive(g_fsm_mutex, portMAX_DELAY);
    g_agent_connected = connected;
    xSemaphoreGiveRecursive(g_fsm_mutex);
}

/**
 * Atomically retrieves telemetry snapshots for status publishing.
 */
static void fsm_get_telemetry_snapshot(int32_t* out_state, cdpr_servo_status_t* out_servo) {
    if (g_fsm_mutex == NULL) return;
    xSemaphoreTakeRecursive(g_fsm_mutex, portMAX_DELAY);
    if (out_state) *out_state = (int32_t)g_current_state;
    if (out_servo) *out_servo = g_servo_status;
    xSemaphoreGiveRecursive(g_fsm_mutex);
}

/**
 * Cable motion command subscription callback (/cdpr/cables/command).
 * Full validation and actuation dispatch performed under mutex protection.
 */
static void on_cable_command_callback(const void* msg_in) {
    const sensor_msgs__msg__JointState* msg = (const sensor_msgs__msg__JointState*) msg_in;
    if (msg == NULL) return;

    int64_t now_us = esp_timer_get_time();

    if (g_fsm_mutex == NULL) return;
    xSemaphoreTakeRecursive(g_fsm_mutex, portMAX_DELAY);

    const double* lengths = (msg->position.data != NULL) ? msg->position.data : NULL;
    size_t num_lengths = msg->position.size;
    const double* rates = (msg->velocity.data != NULL && msg->velocity.size == 4) ? msg->velocity.data : NULL;
    size_t num_rates = msg->velocity.size;

    int32_t stamp_sec = msg->header.stamp.sec;
    uint32_t stamp_nanosec = msg->header.stamp.nanosec;

    cdpr_cmd_validation_result_t vres = cdpr_validate_command(
        lengths, num_lengths, rates, num_rates,
        stamp_sec, stamp_nanosec, g_current_state, &g_cmd_tracker
    );

    if (vres != CDPR_CMD_VALID) {
        ESP_LOGW(TAG, "Cable command REJECTED: %s (Current state: %s)",
                 cdpr_cmd_validation_result_to_str(vres), cdpr_state_to_str(g_current_state));
        xSemaphoreGiveRecursive(g_fsm_mutex);
        return;
    }

    /* Valid command received */
    g_last_valid_command_time_us = now_us;

    if (g_current_state == STATE_MOTION_ENABLED) {
        float rates_f[4] = {0.0f, 0.0f, 0.0f, 0.0f};
        if (rates != NULL) {
            for (int i = 0; i < 4; i++) {
                rates_f[i] = (float)rates[i];
            }
        }
        cdpr_servo_result_t sres = cdpr_servo_command_rates(&g_servo_status, rates_f);
        if (sres != CDPR_SERVO_OK) {
            ESP_LOGW(TAG, "Servo command rejected by driver interface: %d", sres);
        }
    } else if (g_current_state == STATE_READY) {
        ESP_LOGD(TAG, "Valid command received while READY (disarmed, torque software-disabled).");
    }

    xSemaphoreGiveRecursive(g_fsm_mutex);
}

/**
 * Supervisor control command subscription callback (/cdpr/command/control).
 * Explicit disarm, arming request, or latch reset.
 */
static void on_control_command_callback(const void* msg_in) {
    const std_msgs__msg__Int32* msg = (const std_msgs__msg__Int32*) msg_in;
    if (msg == NULL) return;

    if (g_fsm_mutex == NULL) return;
    xSemaphoreTakeRecursive(g_fsm_mutex, portMAX_DELAY);

    switch (msg->data) {
        case CDPR_CMD_DISARM_OR_SAFE_STOP:
            ESP_LOGW(TAG, "Operator control: Request DISARM / SAFE_STOP");
            (void)fsm_transition_locked(STATE_SAFE_STOP);
            break;

        case CDPR_CMD_REQUEST_ARM:
            ESP_LOGI(TAG, "Operator control: Request ARM / MOTION_ENABLED");
            if (!g_servo_status.is_hardware_verified) {
                ESP_LOGE(TAG, "ARM REFUSED: Drive hardware is unverified. Motors remain disarmed (torque software-disabled; physical STO unverified/not wired).");
            } else {
                (void)fsm_transition_locked(STATE_MOTION_ENABLED);
            }
            break;

        case CDPR_CMD_RESET_SAFE_STOP:
            ESP_LOGI(TAG, "Operator control: Request RESET_SAFE_STOP");
            if (g_current_state == STATE_SAFE_STOP || g_current_state == STATE_FAULT) {
                if (!g_agent_connected && g_current_state == STATE_SAFE_STOP) {
                    ESP_LOGW(TAG, "RESET REFUSED: micro-ROS Agent is not connected.");
                } else if (g_servo_status.active_drive_faults != 0) {
                    ESP_LOGW(TAG, "RESET REFUSED: Active drive faults present (%lu).",
                             (unsigned long)g_servo_status.active_drive_faults);
                } else {
                    /* If cleanup failure was latched, execute deliberate verified recovery procedure */
                    if (atomic_load_explicit(&g_cleanup_failed_latched, memory_order_acquire)) {
                        if (!cdpr_recover_unresolved_lifecycle()) {
                            ESP_LOGE(TAG, "RESET REFUSED: Deliberate lifecycle recovery failed to resolve uncleaned resources (Fail-closed).");
                            break;
                        }
                    }
                    g_reset_requested = true;
                    if (g_current_state == STATE_FAULT) {
                        (void)fsm_transition_locked(STATE_INITIALIZING);
                    } else {
                        (void)fsm_transition_locked(STATE_READY);
                    }
                }
            } else {
                ESP_LOGW(TAG, "RESET ignored: Current state is [%s], not SAFE_STOP or FAULT.",
                         cdpr_state_to_str(g_current_state));
            }
            break;

        case CDPR_CMD_EMERGENCY_FAULT:
            ESP_LOGE(TAG, "Operator control: Emergency FAULT commanded.");
            (void)fsm_transition_locked(STATE_FAULT);
            break;

        default:
            ESP_LOGW(TAG, "Unknown operator control command code: %ld", (long)msg->data);
            break;
    }

    xSemaphoreGiveRecursive(g_fsm_mutex);
}

/**
 * Tears down initialized micro-ROS entities cleanly, idempotently, and in strict dependency order.
 *
 * Requirements:
 * 1. Checks explicit return codes of every finalization and destruction API.
 * 2. Does NOT mark an entity as finalized when its finalization call fails.
 * 3. Handles micro_ros_utilities_destroy_message_memory() bool return explicitly.
 * 4. Respects ROS entity dependency order:
 *    - Executor finalized first.
 *    - Dynamic message memory destroyed.
 *    - Subscriptions and publishers finalized.
 *    - Node finalized ONLY if all subscriptions and publishers were finalized.
 *    - Support context finalized ONLY if node was finalized.
 * 5. Verifies executor is not spinning before destroying message memory or entities.
 * 6. Returns true if all entities are cleanly finalized (or already clean); false if any error occurred.
 */
static bool destroy_microros_entities(void) {
    ESP_LOGI(TAG, "Executing micro-ROS entity teardown...");

    /* Prevent reentrant destruction from within an executor callback on the same task */
    if (cdpr_is_executor_spinning_on_current_task()) {
        ESP_LOGE(TAG, "Teardown aborted: Cannot finalize executor from within an active executor callback (preventing use-after-free and self-deadlock).");
        atomic_store_explicit(&g_cleanup_failed_latched, true, memory_order_release);
        return false;
    }

    atomic_store_explicit(&g_teardown_in_progress, true, memory_order_release);

    if (g_executor_mutex == NULL || g_fsm_mutex == NULL) {
        ESP_LOGE(TAG, "Teardown aborted: Synchronization mutex uninitialized! Refusing cleanup (Fail-closed).");
        atomic_store_explicit(&g_cleanup_failed_latched, true, memory_order_release);
        return false;
    }

    bool acquired_executor_lock = false;
    /* Bounded wait for any active executor spin to complete (up to EXECUTOR_TEARDOWN_TIMEOUT_MS) */
    acquired_executor_lock = (xSemaphoreTake(g_executor_mutex, pdMS_TO_TICKS(EXECUTOR_TEARDOWN_TIMEOUT_MS)) == pdTRUE);
    if (!acquired_executor_lock) {
        ESP_LOGE(TAG, "Teardown aborted: Timed out waiting for executor ownership (%d ms). Refusing cleanup (Fail-closed).", EXECUTOR_TEARDOWN_TIMEOUT_MS);
        /* DEFECT FIX: Latch cleanup failure and keep gate permanently closed */
        atomic_store_explicit(&g_cleanup_failed_latched, true, memory_order_release);
        return false;
    }

    xSemaphoreTakeRecursive(g_fsm_mutex, portMAX_DELAY);

    bool all_clean = true;

    /* --- Stage 1: Executor Finalization --- */
    if (g_lifecycle.executor_init) {
        rcl_ret_t rc = rclc_executor_fini(&g_executor);
        if (rc == RCL_RET_OK) {
            g_lifecycle.executor_init = false;
            g_lifecycle.cmd_sub_in_executor = false;
            g_lifecycle.ctrl_sub_in_executor = false;
            ESP_LOGI(TAG, "Executor finalized successfully.");
        } else {
            ESP_LOGE(TAG, "Failed to finalize executor: rcl_ret_t = %d", (int)rc);
            all_clean = false;
        }
    }

    /* --- Stage 2: Dynamic Message Memory Destruction --- */
    micro_ros_utilities_memory_conf_t conf = micro_ros_utilities_memory_conf_default;
    conf.max_string_capacity = 32;
    conf.max_basic_type_sequence_capacity = 4;

    if (g_lifecycle.cmd_msg_memory) {
        bool ok = micro_ros_utilities_destroy_message_memory(
            ROSIDL_GET_MSG_TYPE_SUPPORT(sensor_msgs, msg, JointState),
            &g_cmd_msg, conf);
        if (ok) {
            g_lifecycle.cmd_msg_memory = false;
            ESP_LOGI(TAG, "cmd_msg dynamic memory freed successfully.");
        } else {
            ESP_LOGE(TAG, "Failed to destroy cmd_msg dynamic memory!");
            all_clean = false;
        }
    }

    if (g_lifecycle.feedback_msg_memory) {
        bool ok = micro_ros_utilities_destroy_message_memory(
            ROSIDL_GET_MSG_TYPE_SUPPORT(sensor_msgs, msg, JointState),
            &g_feedback_msg, conf);
        if (ok) {
            g_lifecycle.feedback_msg_memory = false;
            ESP_LOGI(TAG, "feedback_msg dynamic memory freed successfully.");
        } else {
            ESP_LOGE(TAG, "Failed to destroy feedback_msg dynamic memory!");
            all_clean = false;
        }
    }

    /* --- Stage 3: Subscriptions and Publishers Finalization --- */
    if (g_lifecycle.ctrl_sub_init) {
        rcl_ret_t rc = rcl_subscription_fini(&g_ctrl_sub, &g_node);
        if (rc == RCL_RET_OK) {
            g_lifecycle.ctrl_sub_init = false;
            ESP_LOGI(TAG, "ctrl_sub finalized successfully.");
        } else {
            ESP_LOGE(TAG, "Failed to finalize ctrl_sub: rcl_ret_t = %d", (int)rc);
            all_clean = false;
        }
    }

    if (g_lifecycle.cmd_sub_init) {
        rcl_ret_t rc = rcl_subscription_fini(&g_cmd_sub, &g_node);
        if (rc == RCL_RET_OK) {
            g_lifecycle.cmd_sub_init = false;
            ESP_LOGI(TAG, "cmd_sub finalized successfully.");
        } else {
            ESP_LOGE(TAG, "Failed to finalize cmd_sub: rcl_ret_t = %d", (int)rc);
            all_clean = false;
        }
    }

    if (g_lifecycle.feedback_valid_pub_init) {
        rcl_ret_t rc = rcl_publisher_fini(&g_feedback_valid_pub, &g_node);
        if (rc == RCL_RET_OK) {
            g_lifecycle.feedback_valid_pub_init = false;
            ESP_LOGI(TAG, "feedback_valid_pub finalized successfully.");
        } else {
            ESP_LOGE(TAG, "Failed to finalize feedback_valid_pub: rcl_ret_t = %d", (int)rc);
            all_clean = false;
        }
    }

    if (g_lifecycle.status_pub_init) {
        rcl_ret_t rc = rcl_publisher_fini(&g_status_pub, &g_node);
        if (rc == RCL_RET_OK) {
            g_lifecycle.status_pub_init = false;
            ESP_LOGI(TAG, "status_pub finalized successfully.");
        } else {
            ESP_LOGE(TAG, "Failed to finalize status_pub: rcl_ret_t = %d", (int)rc);
            all_clean = false;
        }
    }

    if (g_lifecycle.feedback_pub_init) {
        rcl_ret_t rc = rcl_publisher_fini(&g_feedback_pub, &g_node);
        if (rc == RCL_RET_OK) {
            g_lifecycle.feedback_pub_init = false;
            ESP_LOGI(TAG, "feedback_pub finalized successfully.");
        } else {
            ESP_LOGE(TAG, "Failed to finalize feedback_pub: rcl_ret_t = %d", (int)rc);
            all_clean = false;
        }
    }

    /* --- Stage 4: Node Finalization (Strict Dependency Check) --- */
    bool node_has_dependents = (
        g_lifecycle.cmd_sub_init ||
        g_lifecycle.ctrl_sub_init ||
        g_lifecycle.feedback_pub_init ||
        g_lifecycle.status_pub_init ||
        g_lifecycle.feedback_valid_pub_init
    );

    if (g_lifecycle.node_init) {
        if (node_has_dependents) {
            ESP_LOGE(TAG, "Dependency violation: Cannot finalize rcl_node while dependent publishers or subscriptions remain active!");
            all_clean = false;
        } else {
            rcl_ret_t rc = rcl_node_fini(&g_node);
            if (rc == RCL_RET_OK) {
                g_lifecycle.node_init = false;
                ESP_LOGI(TAG, "Node finalized successfully.");
            } else {
                ESP_LOGE(TAG, "Failed to finalize rcl_node: rcl_ret_t = %d", (int)rc);
                all_clean = false;
            }
        }
    }

    /* --- Stage 5: Support Context Finalization (Strict Dependency Check) --- */
    if (g_lifecycle.support_init) {
        if (g_lifecycle.node_init) {
            ESP_LOGE(TAG, "Dependency violation: Cannot finalize rclc_support while node remains initialized!");
            all_clean = false;
        } else {
            rcl_ret_t rc = rclc_support_fini(&g_support);
            if (rc == RCL_RET_OK) {
                g_lifecycle.support_init = false;
                ESP_LOGI(TAG, "Support context finalized successfully.");
            } else {
                ESP_LOGE(TAG, "Failed to finalize rclc_support: rcl_ret_t = %d", (int)rc);
                all_clean = false;
            }
        }
    }

    bool has_unresolved = cdpr_has_unresolved_entities(&g_lifecycle);

    if (g_fsm_mutex != NULL) {
        xSemaphoreGiveRecursive(g_fsm_mutex);
    }

    if (acquired_executor_lock) {
        xSemaphoreGive(g_executor_mutex);
    }

    /* Fail-closed completion check:
     * If a cleanup failure was already latched from a prior failure, ordinary teardown CANNOT clear it.
     * Only the deliberate, verified recovery procedure cdpr_recover_unresolved_lifecycle()
     * is authorized to clear g_cleanup_failed_latched after verified full finalization. */
    if (all_clean && !has_unresolved) {
        if (!atomic_load_explicit(&g_cleanup_failed_latched, memory_order_acquire)) {
            atomic_store_explicit(&g_teardown_in_progress, false, memory_order_release);
        }
        ESP_LOGI(TAG, "micro-ROS entity teardown completed successfully (all entities clean).");
    } else {
        /* Fail-closed: latch failure permanently; do NOT clear g_teardown_in_progress */
        atomic_store_explicit(&g_cleanup_failed_latched, true, memory_order_release);
        ESP_LOGE(TAG, "micro-ROS entity teardown completed WITH UNRESOLVED ENTITIES! Gate remains latched CLOSED (Fail-closed).");
    }

    return all_clean;
}

/**
 * Deliberate, verified lifecycle recovery procedure.
 * Bounded, repeatable, and fail-closed.
 *
 * Requirements:
 * 1. Checks that executor is not spinning on current task.
 * 2. Executes entity teardown pass to resolve any remaining entities.
 * 3. Takes g_executor_mutex (bounded timeout) and g_fsm_mutex.
 * 4. Strictly verifies:
 *    - clean == true
 *    - !cdpr_has_unresolved_entities(&g_lifecycle)
 *    - !g_lifecycle.cmd_msg_memory && !g_lifecycle.feedback_msg_memory
 * 5. ONLY when every entity and allocated buffer is confirmed resolved:
 *    clears g_cleanup_failed_latched = false and g_teardown_in_progress = false.
 *    Returns true.
 * 6. If any resource remains unresolved, leaves g_cleanup_failed_latched = true and returns false.
 */
static bool cdpr_recover_unresolved_lifecycle(void) {
    ESP_LOGI(TAG, "Executing deliberate micro-ROS lifecycle recovery procedure...");

    if (cdpr_is_executor_spinning_on_current_task()) {
        ESP_LOGE(TAG, "Recovery refused: Cannot execute recovery from within an active executor callback.");
        return false;
    }

    if (g_executor_mutex == NULL || g_fsm_mutex == NULL) {
        ESP_LOGE(TAG, "Recovery refused: Synchronization mutex uninitialized.");
        return false;
    }

    /* Perform teardown pass to clean any unresolved entities */
    bool clean = destroy_microros_entities();

    /* Bounded lock to verify entity status under mutex protection */
    if (xSemaphoreTake(g_executor_mutex, pdMS_TO_TICKS(EXECUTOR_TEARDOWN_TIMEOUT_MS)) != pdTRUE) {
        ESP_LOGE(TAG, "Recovery refused: Timed out acquiring executor mutex for recovery verification.");
        return false;
    }

    xSemaphoreTakeRecursive(g_fsm_mutex, portMAX_DELAY);

    bool recovery_ok = clean && !cdpr_has_unresolved_entities(&g_lifecycle) &&
                       !g_lifecycle.cmd_msg_memory && !g_lifecycle.feedback_msg_memory;

    if (recovery_ok) {
        atomic_store_explicit(&g_cleanup_failed_latched, false, memory_order_release);
        atomic_store_explicit(&g_teardown_in_progress, false, memory_order_release);
        ESP_LOGI(TAG, "Deliberate recovery verified safe: All entities confirmed resolved. Admission gate reopened.");
    } else {
        atomic_store_explicit(&g_cleanup_failed_latched, true, memory_order_release);
        ESP_LOGE(TAG, "Recovery verification failed: Unresolved entities or memory remain! Gate remains latched CLOSED (Fail-closed).");
    }

    xSemaphoreGiveRecursive(g_fsm_mutex);
    xSemaphoreGive(g_executor_mutex);

    return recovery_ok;
}

/**
 * Initializes micro-ROS support, node, subscribers, publishers, and executor.
 * On any failure, cleans up partially initialized entities safely via destroy_microros_entities().
 */
static bool create_microros_entities(void) {
    ESP_LOGI(TAG, "Initializing micro-ROS entities...");

    if (g_executor_mutex == NULL) return false;

    /* Refuse creation if teardown is in progress, any entity remains unresolved from previous failed teardown, or cleanup failure is latched */
    if (atomic_load_explicit(&g_teardown_in_progress, memory_order_acquire) ||
        atomic_load_explicit(&g_cleanup_failed_latched, memory_order_acquire)) {
        ESP_LOGE(TAG, "Cannot create micro-ROS entities: Teardown in progress or cleanup failure latched! Refusing initialization (Fail-closed).");
        return false;
    }

    if (xSemaphoreTake(g_executor_mutex, pdMS_TO_TICKS(EXECUTOR_TEARDOWN_TIMEOUT_MS)) != pdTRUE) {
        ESP_LOGE(TAG, "Cannot create micro-ROS entities: Timed out waiting for executor mutex.");
        return false;
    }

    if (g_fsm_mutex != NULL) {
        xSemaphoreTakeRecursive(g_fsm_mutex, portMAX_DELAY);
    }

    /* Check unresolved entities under mutex protection */
    if (cdpr_has_unresolved_entities(&g_lifecycle) ||
        atomic_load_explicit(&g_teardown_in_progress, memory_order_acquire) ||
        atomic_load_explicit(&g_cleanup_failed_latched, memory_order_acquire)) {
        if (g_fsm_mutex != NULL) {
            xSemaphoreGiveRecursive(g_fsm_mutex);
        }
        xSemaphoreGive(g_executor_mutex);
        ESP_LOGE(TAG, "Cannot create micro-ROS entities: Unresolved entities remain or failure latched under mutex!");
        return false;
    }

    memset(&g_lifecycle, 0, sizeof(g_lifecycle));
    if (g_fsm_mutex != NULL) {
        xSemaphoreGiveRecursive(g_fsm_mutex);
    }
    xSemaphoreGive(g_executor_mutex);
    g_allocator = rcl_get_default_allocator();

    rcl_ret_t rc = rclc_support_init(&g_support, 0, NULL, &g_allocator);
    if (rc != RCL_RET_OK) {
        ESP_LOGE(TAG, "Failed to init support: %d", (int)rc);
        (void)destroy_microros_entities();
        return false;
    }
    g_lifecycle.support_init = true;

    rc = rclc_node_init_default(&g_node, "cdpr_esp32_firmware", "", &g_support);
    if (rc != RCL_RET_OK) {
        ESP_LOGE(TAG, "Failed to init node: %d", (int)rc);
        (void)destroy_microros_entities();
        return false;
    }
    g_lifecycle.node_init = true;

    rc = rclc_subscription_init_default(
        &g_cmd_sub, &g_node,
        ROSIDL_GET_MSG_TYPE_SUPPORT(sensor_msgs, msg, JointState),
        "/cdpr/cables/command"
    );
    if (rc != RCL_RET_OK) {
        ESP_LOGE(TAG, "Failed to init cmd subscription: %d", (int)rc);
        (void)destroy_microros_entities();
        return false;
    }
    g_lifecycle.cmd_sub_init = true;

    rc = rclc_subscription_init_default(
        &g_ctrl_sub, &g_node,
        ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Int32),
        "/cdpr/command/control"
    );
    if (rc != RCL_RET_OK) {
        ESP_LOGE(TAG, "Failed to init ctrl subscription: %d", (int)rc);
        (void)destroy_microros_entities();
        return false;
    }
    g_lifecycle.ctrl_sub_init = true;

    rc = rclc_publisher_init_default(
        &g_feedback_pub, &g_node,
        ROSIDL_GET_MSG_TYPE_SUPPORT(sensor_msgs, msg, JointState),
        "/cdpr/cables/feedback"
    );
    if (rc != RCL_RET_OK) {
        ESP_LOGE(TAG, "Failed to init feedback publisher: %d", (int)rc);
        (void)destroy_microros_entities();
        return false;
    }
    g_lifecycle.feedback_pub_init = true;

    rc = rclc_publisher_init_default(
        &g_status_pub, &g_node,
        ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Int32),
        "/cdpr/firmware/status"
    );
    if (rc != RCL_RET_OK) {
        ESP_LOGE(TAG, "Failed to init status publisher: %d", (int)rc);
        (void)destroy_microros_entities();
        return false;
    }
    g_lifecycle.status_pub_init = true;

    rc = rclc_publisher_init_default(
        &g_feedback_valid_pub, &g_node,
        ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Bool),
        "/cdpr/feedback/valid"
    );
    if (rc != RCL_RET_OK) {
        ESP_LOGE(TAG, "Failed to init feedback_valid publisher: %d", (int)rc);
        (void)destroy_microros_entities();
        return false;
    }
    g_lifecycle.feedback_valid_pub_init = true;

    /* Pre-allocate dynamic sequence memory for JointState messages (4 joints) */
    micro_ros_utilities_memory_conf_t conf = micro_ros_utilities_memory_conf_default;
    conf.max_string_capacity = 32;
    conf.max_basic_type_sequence_capacity = 4;

    if (!micro_ros_utilities_create_message_memory(
            ROSIDL_GET_MSG_TYPE_SUPPORT(sensor_msgs, msg, JointState),
            &g_cmd_msg, conf)) {
        ESP_LOGE(TAG, "Failed to allocate memory for cmd_msg");
        (void)destroy_microros_entities();
        return false;
    }
    g_lifecycle.cmd_msg_memory = true;

    if (!micro_ros_utilities_create_message_memory(
            ROSIDL_GET_MSG_TYPE_SUPPORT(sensor_msgs, msg, JointState),
            &g_feedback_msg, conf)) {
        ESP_LOGE(TAG, "Failed to allocate memory for feedback_msg");
        (void)destroy_microros_entities();
        return false;
    }
    g_lifecycle.feedback_msg_memory = true;

    /* Initialize executor with 2 subscription handles */
    rc = rclc_executor_init(&g_executor, &g_support.context, 2, &g_allocator);
    if (rc != RCL_RET_OK) {
        ESP_LOGE(TAG, "Failed to init executor: %d", (int)rc);
        (void)destroy_microros_entities();
        return false;
    }
    g_lifecycle.executor_init = true;

    rc = rclc_executor_add_subscription(
        &g_executor, &g_cmd_sub, &g_cmd_msg,
        on_cable_command_callback, ON_NEW_DATA
    );
    if (rc != RCL_RET_OK) {
        ESP_LOGE(TAG, "Failed to add cmd_sub to executor: %d", (int)rc);
        (void)destroy_microros_entities();
        return false;
    }
    g_lifecycle.cmd_sub_in_executor = true;

    rc = rclc_executor_add_subscription(
        &g_executor, &g_ctrl_sub, &g_ctrl_msg,
        on_control_command_callback, ON_NEW_DATA
    );
    if (rc != RCL_RET_OK) {
        ESP_LOGE(TAG, "Failed to add ctrl_sub to executor: %d", (int)rc);
        (void)destroy_microros_entities();
        return false;
    }
    g_lifecycle.ctrl_sub_in_executor = true;

    ESP_LOGI(TAG, "micro-ROS entities initialized successfully.");
    return true;
}

/**
 * Main micro-ROS FreeRTOS Task.
 */
void micro_ros_task(void* arg) {
    ESP_LOGI(TAG, "Booting CDPR firmware. Starting initialization...");
    (void)fsm_transition_to(STATE_INITIALIZING);

    if (g_fsm_mutex != NULL) {
        xSemaphoreTakeRecursive(g_fsm_mutex, portMAX_DELAY);
        cdpr_command_tracker_init(&g_cmd_tracker);

        /* Initialize physical servo peripheral interface stub (unverified, torque software-disabled) */
        cdpr_servo_result_t init_res = cdpr_servo_init(&g_servo_status);
        if (init_res != CDPR_SERVO_OK) {
            ESP_LOGW(TAG, "Servo interface initialized as UNVERIFIED STUB (code %d). Torque locked.", init_res);
        }
        xSemaphoreGiveRecursive(g_fsm_mutex);
    }

    (void)fsm_transition_to(STATE_WAITING_FOR_AGENT);

    int64_t last_ping_time_us = 0;
    int64_t last_status_pub_time_us = 0;
    int consecutive_spin_errors = 0;

    while (1) {
        int64_t now_us = esp_timer_get_time();
        cdpr_firmware_state_t st = fsm_get_state();

        switch (st) {
            case STATE_WAITING_FOR_AGENT: {
                if ((now_us - last_ping_time_us) > (AGENT_DISCOVERY_INTERVAL_MS * 1000)) {
                    last_ping_time_us = now_us;
                    rmw_ret_t ping_rc = rmw_uros_ping_agent(AGENT_PING_TIMEOUT_MS, AGENT_PING_ATTEMPTS);
                    if (ping_rc == RMW_RET_OK) {
                        ESP_LOGI(TAG, "micro-ROS Agent discovered on UART2!");
                        fsm_set_agent_connected(true);
                        (void)fsm_transition_to(STATE_CONNECTED);
                    } else {
                        ESP_LOGD(TAG, "Waiting for micro-ROS Agent on UART2...");
                    }
                }
                vTaskDelay(pdMS_TO_TICKS(100));
                break;
            }

            case STATE_CONNECTED: {
                if (create_microros_entities()) {
                    (void)fsm_transition_to(STATE_DRIVE_STATUS_CHECK);
                } else {
                    fsm_set_agent_connected(false);
                    if (cdpr_has_unresolved_entities(&g_lifecycle) ||
                        atomic_load_explicit(&g_cleanup_failed_latched, memory_order_acquire)) {
                        ESP_LOGE(TAG, "Entity creation failed with UNRESOLVED entities or latched cleanup failure! Transitioning to STATE_FAULT (Fail-closed).");
                        (void)fsm_transition_to(STATE_FAULT);
                    } else {
                        ESP_LOGE(TAG, "Entity creation failed. Retrying in 2 seconds...");
                        (void)fsm_transition_to(STATE_WAITING_FOR_AGENT);
                        vTaskDelay(pdMS_TO_TICKS(2000));
                    }
                }
                break;
            }

            case STATE_DRIVE_STATUS_CHECK: {
                if (g_fsm_mutex != NULL) {
                    xSemaphoreTakeRecursive(g_fsm_mutex, portMAX_DELAY);
                    cdpr_servo_result_t drv_res = cdpr_servo_read_status(&g_servo_status);
                    if (drv_res != CDPR_SERVO_OK) {
                        ESP_LOGW(TAG, "Drive status check: Hardware UNVERIFIED (code %d). Motors remain disarmed (torque software-disabled).", drv_res);
                    }
                    xSemaphoreGiveRecursive(g_fsm_mutex);
                }
                /* Transition to READY (safe disarmed idle state) */
                (void)fsm_transition_to(STATE_READY);
                break;
            }

            case STATE_READY:
            case STATE_MOTION_ENABLED:
            case STATE_SAFE_STOP: {
                if (!g_lifecycle.executor_init) {
                    vTaskDelay(pdMS_TO_TICKS(100));
                    break;
                }

                /* Synchronized bounded spin (10 ms timeout) */
                if (cdpr_executor_acquire_for_spin(pdMS_TO_TICKS(EXECUTOR_SPIN_TIMEOUT_MS))) {
                    rcl_ret_t spin_rc = rclc_executor_spin_some(&g_executor, RCL_MS_TO_NS(EXECUTOR_SPIN_TIMEOUT_MS));
                    cdpr_executor_release_from_spin();

                    if (spin_rc != RCL_RET_OK && spin_rc != RCL_RET_TIMEOUT) {
                        consecutive_spin_errors++;
                        if (consecutive_spin_errors > 5) {
                            ESP_LOGE(TAG, "Excessive executor spin errors (%d). Declaring Agent loss.", consecutive_spin_errors);
                            fsm_handle_agent_disconnect();
                            consecutive_spin_errors = 0;
                            break;
                        }
                    } else {
                        consecutive_spin_errors = 0;
                    }
                }

                /* Process deferred disconnect if initiated from within an executor callback */
                if (atomic_exchange_explicit(&g_disconnect_pending, false, memory_order_acq_rel)) {
                    fsm_handle_agent_disconnect();
                    break;
                }

                /* Check watchdog if in MOTION_ENABLED */
                fsm_check_watchdog(now_us);

                /* Publish periodic telemetry & status */
                if ((now_us - last_status_pub_time_us) > (STATUS_PUBLISH_INTERVAL_MS * 1000)) {
                    last_status_pub_time_us = now_us;

                    if (g_fsm_mutex != NULL && xSemaphoreTakeRecursive(g_fsm_mutex, pdMS_TO_TICKS(20)) == pdTRUE) {
                        if (g_lifecycle.status_pub_init && g_lifecycle.feedback_pub_init && g_lifecycle.feedback_valid_pub_init) {
                            int32_t current_state_num = 0;
                            cdpr_servo_status_t servo_snap;
                            fsm_get_telemetry_snapshot(&current_state_num, &servo_snap);

                            /* Publish firmware state */
                            g_status_msg.data = current_state_num;
                            rcl_ret_t rc_pub = rcl_publish(&g_status_pub, &g_status_msg, NULL);
                            if (rc_pub != RCL_RET_OK) {
                                ESP_LOGD(TAG, "Status publish returned %d", (int)rc_pub);
                            }

                            /* Format feedback using strict fail-closed validity rules */
                            cdpr_feedback_payload_t payload;
                            cdpr_format_feedback_payload(&servo_snap, &payload);

                            g_feedback_msg.header.stamp.sec = (int32_t)(now_us / 1000000);
                            g_feedback_msg.header.stamp.nanosec = (uint32_t)((now_us % 1000000) * 1000);

                            if (g_feedback_msg.header.frame_id.data != NULL && g_feedback_msg.header.frame_id.capacity > 0) {
                                snprintf(g_feedback_msg.header.frame_id.data, g_feedback_msg.header.frame_id.capacity,
                                         "%s", payload.frame_id);
                                g_feedback_msg.header.frame_id.size = strlen(g_feedback_msg.header.frame_id.data);
                            }

                            /* Explicit encoderless / unavailable feedback convention:
                             * When hardware is unverified or sensors are unavailable:
                             * - position.size = 0, velocity.size = 0, effort.size = 0, name.size = 0.
                             * - NO fabricated measurements or dummy zeros are published.
                             * - header.frame_id is "cdpr_feedback_unavailable".
                             * - /cdpr/feedback/valid publishes data = false.
                             */
                            g_feedback_msg.name.size = 0;
                            g_feedback_msg.position.size = payload.num_joints;
                            g_feedback_msg.velocity.size = payload.num_joints;
                            g_feedback_msg.effort.size = 0;

                            if (payload.is_valid && payload.num_joints == 4) {
                                for (size_t i = 0; i < 4; i++) {
                                    g_feedback_msg.position.data[i] = payload.lengths_m[i];
                                    g_feedback_msg.velocity.data[i] = payload.rates_m_s[i];
                                }
                            }

                            rc_pub = rcl_publish(&g_feedback_pub, &g_feedback_msg, NULL);
                            if (rc_pub != RCL_RET_OK) {
                                ESP_LOGD(TAG, "Feedback publish returned %d", (int)rc_pub);
                            }

                            /* Publish dedicated feedback validity status topic */
                            g_feedback_valid_msg.data = payload.is_valid;
                            rc_pub = rcl_publish(&g_feedback_valid_pub, &g_feedback_valid_msg, NULL);
                            if (rc_pub != RCL_RET_OK) {
                                ESP_LOGD(TAG, "Feedback valid publish returned %d", (int)rc_pub);
                            }
                        }
                        xSemaphoreGiveRecursive(g_fsm_mutex);
                    }
                }

                /* Periodic Agent liveness check (every 2 seconds) */
                if ((now_us - last_ping_time_us) > (AGENT_LIVENESS_CHECK_INTERVAL_MS * 1000)) {
                    last_ping_time_us = now_us;
                    rmw_ret_t ping_rc = rmw_uros_ping_agent(AGENT_PING_TIMEOUT_MS, AGENT_PING_ATTEMPTS);
                    if (ping_rc != RMW_RET_OK) {
                        ESP_LOGE(TAG, "Agent liveness ping failed! Declaring Agent disconnection.");
                        fsm_handle_agent_disconnect();
                    }
                }

                vTaskDelay(pdMS_TO_TICKS(5));
                break;
            }

            case STATE_FAULT: {
                /* In STATE_FAULT, background spin and ping disconnect loops are inhibited.
                 * Motors are safe-stopped and disarmed.
                 * Deliberate recovery requires explicit operator reset or hard initialization. */
                bool do_recovery = false;
                if (g_fsm_mutex != NULL) {
                    xSemaphoreTakeRecursive(g_fsm_mutex, portMAX_DELAY);
                    if (g_reset_requested) {
                        g_reset_requested = false;
                        do_recovery = true;
                    }
                    xSemaphoreGiveRecursive(g_fsm_mutex);
                }
                if (do_recovery) {
                    if (atomic_load_explicit(&g_cleanup_failed_latched, memory_order_acquire)) {
                        if (cdpr_recover_unresolved_lifecycle()) {
                            ESP_LOGI(TAG, "STATE_FAULT: Lifecycle recovered cleanly. Re-initializing...");
                            (void)fsm_transition_to(STATE_INITIALIZING);
                        } else {
                            ESP_LOGE(TAG, "STATE_FAULT: Lifecycle recovery failed. Remaining in STATE_FAULT.");
                        }
                    } else {
                        (void)fsm_transition_to(STATE_INITIALIZING);
                    }
                }
                vTaskDelay(pdMS_TO_TICKS(100));
                break;
            }

            default:
                vTaskDelay(pdMS_TO_TICKS(100));
                break;
        }
    }
}

void app_main(void) {
    ESP_LOGI(TAG, "Booting CDPR ESP32 Micro-ROS Firmware...");

    g_fsm_mutex = xSemaphoreCreateRecursiveMutex();
    if (g_fsm_mutex == NULL) {
        ESP_LOGE(TAG, "FATAL: Could not create FSM recursive mutex.");
        return;
    }

    g_executor_mutex = xSemaphoreCreateMutex();
    if (g_executor_mutex == NULL) {
        ESP_LOGE(TAG, "FATAL: Could not create executor mutex.");
        return;
    }

    atomic_init(&g_teardown_in_progress, false);
    atomic_init(&g_cleanup_failed_latched, false);
    atomic_init(&g_disconnect_pending, false);

#if defined(RMW_UXRCE_TRANSPORT_CUSTOM)
    rmw_ret_t transport_rc = rmw_uros_set_custom_transport(
        true,
        (void*)&g_microros_uart_port,
        esp32_serial_open,
        esp32_serial_close,
        esp32_serial_write,
        esp32_serial_read
    );
    if (transport_rc != RMW_RET_OK) {
        ESP_LOGE(TAG, "FATAL: rmw_uros_set_custom_transport failed (%d)", (int)transport_rc);
        return;
    }
    ESP_LOGI(TAG, "Custom UART transport configured on UART2 (TX=GPIO17, RX=GPIO16, 115200 baud).");
#else
#error "RMW_UXRCE_TRANSPORT_CUSTOM is required for this firmware build"
#endif

    BaseType_t task_rc = xTaskCreate(
        micro_ros_task,
        "micro_ros_task",
        CONFIG_MICRO_ROS_APP_STACK,
        NULL,
        CONFIG_MICRO_ROS_APP_TASK_PRIO,
        NULL
    );
    if (task_rc != pdPASS) {
        ESP_LOGE(TAG, "FATAL: Failed to create micro_ros_task (return code: %d)", (int)task_rc);
        return;
    }
}
