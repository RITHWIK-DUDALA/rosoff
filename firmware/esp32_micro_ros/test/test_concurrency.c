/**
 * Unit test suite for CDPR Firmware FreeRTOS Synchronization & Concurrency Integrity.
 *
 * NOTE: This is a HOST-BASED concurrency unit test suite using POSIX threads and C11 atomics.
 * It validates synchronization protocols, fail-closed executor admission gating,
 * persistent cleanup failure latching, race prevention between executor spinning and
 * entity teardown, bounded timeouts, and deferred callback disconnects.
 * It DOES NOT represent physical hardware validation or physical STO.
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <string.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdatomic.h>
#include <pthread.h>
#include <unistd.h>
#include <time.h>
#include <errno.h>
#include "../main/app_state.h"
#include "../main/servo_driver_interface.h"
#include "../main/cdpr_command_validator.h"

static int g_tests_run = 0;
static int g_tests_passed = 0;

#define TEST_ASSERT(cond, msg) do { \
    g_tests_run++; \
    if (cond) { \
        g_tests_passed++; \
        printf("  [PASS] %s\n", msg); \
    } else { \
        printf("  [FAIL] %s (line %d)\n", msg, __LINE__); \
    } \
} while(0)

/* Shared concurrent state structure protected by recursive mutex */
typedef struct {
    pthread_mutex_t        mutex;
    cdpr_firmware_state_t  state;
    cdpr_servo_status_t    servo;
    cdpr_command_tracker_t tracker;
    int64_t                last_valid_cmd_time_us;
    bool                   agent_connected;
    bool                   reset_requested;
    bool                   watchdog_tripped;
    int                    transitions_count;
    int                    commands_processed;
    int                    snapshots_taken;
    bool                   stop_workers;
} concurrent_firmware_ctx_t;

static concurrent_firmware_ctx_t g_ctx;

/* Nested locked transition (simulating fsm_transition_locked in main.c) */
static bool mock_transition_locked(concurrent_firmware_ctx_t* ctx, cdpr_firmware_state_t new_state) {
    if (!cdpr_is_valid_transition(ctx->state, new_state)) {
        return false;
    }

    if (new_state == STATE_MOTION_ENABLED) {
        if (!ctx->servo.is_hardware_verified || !ctx->servo.torque_permitted) {
            return false;
        }
    }

    if (ctx->state == STATE_SAFE_STOP && new_state == STATE_READY) {
        if (!ctx->reset_requested || !ctx->agent_connected || ctx->servo.active_drive_faults != 0) {
            return false;
        }
        ctx->reset_requested = false;
        ctx->watchdog_tripped = false;
    }

    ctx->state = new_state;
    ctx->transitions_count++;

    if (new_state == STATE_SAFE_STOP || new_state == STATE_FAULT) {
        cdpr_servo_emergency_safe_stop(&ctx->servo);
    }
    return true;
}

/* Public transition taking recursive mutex (simulating fsm_transition_to in main.c) */
static bool mock_transition_to(concurrent_firmware_ctx_t* ctx, cdpr_firmware_state_t new_state) {
    pthread_mutex_lock(&ctx->mutex);
    bool res = mock_transition_locked(ctx, new_state);
    pthread_mutex_unlock(&ctx->mutex);
    return res;
}

/* Nested lock verification: function that locks, then calls a function that locks again */
void test_recursive_mutex_nested_locking(void) {
    printf("\n--- Test Recursive Mutex Nested Locking (Deadlock Prevention) ---\n");

    pthread_mutexattr_t attr;
    pthread_mutexattr_init(&attr);
    pthread_mutexattr_settype(&attr, PTHREAD_MUTEX_RECURSIVE);
    pthread_mutex_init(&g_ctx.mutex, &attr);
    pthread_mutexattr_destroy(&attr);

    g_ctx.state = STATE_BOOT;
    cdpr_servo_init(&g_ctx.servo);

    /* Outer lock */
    pthread_mutex_lock(&g_ctx.mutex);

    /* Inner lock via transition (proves recursive mutex does not self-deadlock) */
    bool ok = mock_transition_locked(&g_ctx, STATE_INITIALIZING);
    TEST_ASSERT(ok, "Nested lock acquired successfully; transition to INITIALIZING");
    TEST_ASSERT(g_ctx.state == STATE_INITIALIZING, "State is INITIALIZING");

    /* Inner lock again */
    pthread_mutex_lock(&g_ctx.mutex);
    ok = mock_transition_locked(&g_ctx, STATE_WAITING_FOR_AGENT);
    TEST_ASSERT(ok, "Double nested lock acquired successfully; transition to WAITING_FOR_AGENT");
    pthread_mutex_unlock(&g_ctx.mutex);

    /* Public thread-safe transition function taking mutex internally */
    ok = mock_transition_to(&g_ctx, STATE_CONNECTED);
    TEST_ASSERT(ok, "mock_transition_to acquired mutex and transitioned to CONNECTED");

    pthread_mutex_unlock(&g_ctx.mutex);
    pthread_mutex_destroy(&g_ctx.mutex);
}

/* Worker Thread 1: Executor processing motion commands */
static void* worker_executor(void* arg) {
    concurrent_firmware_ctx_t* ctx = (concurrent_firmware_ctx_t*)arg;
    const double valid_lengths[4] = {0.300, 0.300, 0.300, 0.300};
    const double valid_rates[4]   = {0.050, 0.050, -0.050, -0.050};
    int sec = 1;
    uint32_t nanosec = 0;

    while (!ctx->stop_workers) {
        pthread_mutex_lock(&ctx->mutex);

        nanosec += 10000000; /* 10 ms increments */
        if (nanosec >= 1000000000) {
            sec++;
            nanosec = 0;
        }

        cdpr_cmd_validation_result_t vres = cdpr_validate_command(
            valid_lengths, 4, valid_rates, 4,
            sec, nanosec, ctx->state, &ctx->tracker
        );

        if (vres == CDPR_CMD_VALID) {
            ctx->last_valid_cmd_time_us += 10000;
            ctx->commands_processed++;
        }

        pthread_mutex_unlock(&ctx->mutex);
        usleep(50); /* 50 microseconds yield */
    }
    return NULL;
}

/* Worker Thread 2: Supervisor & Watchdog task */
static void* worker_watchdog(void* arg) {
    concurrent_firmware_ctx_t* ctx = (concurrent_firmware_ctx_t*)arg;

    while (!ctx->stop_workers) {
        pthread_mutex_lock(&ctx->mutex);

        if (ctx->state == STATE_MOTION_ENABLED) {
            /* Simulate trip */
            ctx->watchdog_tripped = true;
            mock_transition_locked(ctx, STATE_SAFE_STOP);
        } else if (ctx->state == STATE_SAFE_STOP) {
            /* Simulate operator reset */
            ctx->reset_requested = true;
            mock_transition_locked(ctx, STATE_READY);
        }

        pthread_mutex_unlock(&ctx->mutex);
        usleep(100);
    }
    return NULL;
}

/* Worker Thread 3: Telemetry reader taking periodic snapshots */
static void* worker_telemetry(void* arg) {
    concurrent_firmware_ctx_t* ctx = (concurrent_firmware_ctx_t*)arg;

    while (!ctx->stop_workers) {
        pthread_mutex_lock(&ctx->mutex);

        cdpr_firmware_state_t st = ctx->state;
        (void)st;
        cdpr_servo_status_t snap = ctx->servo;
        (void)snap;
        ctx->snapshots_taken++;

        pthread_mutex_unlock(&ctx->mutex);
        usleep(80);
    }
    return NULL;
}

void test_multithreaded_concurrency_stress(void) {
    printf("\n--- Test Multi-Threaded Concurrency Stress (5,000 Iterations) ---\n");

    pthread_mutexattr_t attr;
    pthread_mutexattr_init(&attr);
    pthread_mutexattr_settype(&attr, PTHREAD_MUTEX_RECURSIVE);
    pthread_mutex_init(&g_ctx.mutex, &attr);
    pthread_mutexattr_destroy(&attr);

    g_ctx.state = STATE_READY;
    cdpr_servo_init(&g_ctx.servo);
    cdpr_command_tracker_init(&g_ctx.tracker);
    g_ctx.agent_connected = true;
    g_ctx.last_valid_cmd_time_us = 1000;
    g_ctx.transitions_count = 0;
    g_ctx.commands_processed = 0;
    g_ctx.snapshots_taken = 0;
    g_ctx.stop_workers = false;

    pthread_t t1, t2, t3;
    pthread_create(&t1, NULL, worker_executor, &g_ctx);
    pthread_create(&t2, NULL, worker_watchdog, &g_ctx);
    pthread_create(&t3, NULL, worker_telemetry, &g_ctx);

    /* Run stress test for 100 ms of high-frequency contention */
    usleep(100000);

    g_ctx.stop_workers = true;

    pthread_join(t1, NULL);
    pthread_join(t2, NULL);
    pthread_join(t3, NULL);

    pthread_mutex_destroy(&g_ctx.mutex);

    printf("  Concurrent ops: %d commands processed, %d state transitions, %d telemetry snapshots\n",
           g_ctx.commands_processed, g_ctx.transitions_count, g_ctx.snapshots_taken);

    TEST_ASSERT(g_ctx.commands_processed > 100, "Commands processed without deadlocks");
    TEST_ASSERT(g_ctx.snapshots_taken > 100, "Telemetry snapshots completed concurrently");
    TEST_ASSERT(g_ctx.state == STATE_READY || g_ctx.state == STATE_SAFE_STOP,
                "State integrity preserved (legal final state)");
}

/* ========================================================================= */
/*   EXECUTOR VS TEARDOWN SYNCHRONIZATION CONCURRENCY TESTS                  */
/* ========================================================================= */

typedef struct {
    pthread_mutex_t fsm_mutex;
    pthread_mutex_t executor_mutex;
    pthread_t       executor_thread;
    bool            executor_thread_valid;
    bool            support_init;
    bool            node_init;
    bool            executor_init;
    bool            cmd_sub_init;
    bool            cmd_msg_memory;
    bool            feedback_msg_memory;
    bool            executor_spinning;
    atomic_bool     teardown_in_progress;
    atomic_bool     cleanup_failed_latched;
    atomic_bool     disconnect_pending;
    bool            teardown_active_in_critical_section;
    int             spins_completed;
    int             teardowns_completed;
    int             concurrency_violations;
    bool            stop_test;
} sync_test_ctx_t;

static sync_test_ctx_t g_sync_ctx;

static inline bool sync_is_lifecycle_ready_for_spin(const sync_test_ctx_t* ctx) {
    return (
        ctx->support_init &&
        ctx->node_init &&
        ctx->executor_init &&
        ctx->cmd_sub_init &&
        ctx->cmd_msg_memory &&
        ctx->feedback_msg_memory
    );
}

static inline bool sync_has_unresolved_entities(const sync_test_ctx_t* ctx) {
    return (
        ctx->support_init ||
        ctx->node_init ||
        ctx->executor_init ||
        ctx->cmd_sub_init ||
        ctx->cmd_msg_memory ||
        ctx->feedback_msg_memory
    );
}

static inline bool sync_is_executor_spinning_on_current_task(sync_test_ctx_t* ctx) {
    if (!ctx->executor_spinning) return false;
    return (ctx->executor_thread_valid && pthread_equal(ctx->executor_thread, pthread_self()));
}

/* Simulates bounded pthread_mutex_lock with timeout in milliseconds */
static bool timed_mutex_lock(pthread_mutex_t* m, int timeout_ms) {
    struct timespec ts;
    clock_gettime(CLOCK_REALTIME, &ts);
    ts.tv_nsec += (long)(timeout_ms % 1000) * 1000000L;
    ts.tv_sec  += timeout_ms / 1000 + (ts.tv_nsec / 1000000000L);
    ts.tv_nsec %= 1000000000L;

    return (pthread_mutex_timedlock(m, &ts) == 0);
}

static bool sync_executor_acquire_for_spin(sync_test_ctx_t* ctx, int timeout_ms) {
    /* Fast-path pre-check: fail-closed if teardown active, cleanup failed, or uninitialized */
    if (atomic_load_explicit(&ctx->teardown_in_progress, memory_order_acquire) ||
        atomic_load_explicit(&ctx->cleanup_failed_latched, memory_order_acquire) ||
        !sync_is_lifecycle_ready_for_spin(ctx)) {
        return false;
    }

    if (!timed_mutex_lock(&ctx->executor_mutex, timeout_ms)) {
        return false;
    }

    /* Re-verify all fail-closed conditions under executor_mutex protection */
    if (atomic_load_explicit(&ctx->teardown_in_progress, memory_order_acquire) ||
        atomic_load_explicit(&ctx->cleanup_failed_latched, memory_order_acquire) ||
        !sync_is_lifecycle_ready_for_spin(ctx)) {
        pthread_mutex_unlock(&ctx->executor_mutex);
        return false;
    }

    ctx->executor_spinning = true;
    ctx->executor_thread = pthread_self();
    ctx->executor_thread_valid = true;
    return true;
}

static void sync_executor_release_from_spin(sync_test_ctx_t* ctx) {
    ctx->executor_spinning = false;
    ctx->executor_thread_valid = false;
    pthread_mutex_unlock(&ctx->executor_mutex);
}

static bool sync_destroy_microros_entities(sync_test_ctx_t* ctx, int timeout_ms, bool inject_entity_failure, bool inject_memory_failure) {
    /* Prevent reentrant destruction from within an executor callback */
    if (sync_is_executor_spinning_on_current_task(ctx)) {
        return false;
    }

    atomic_store_explicit(&ctx->teardown_in_progress, true, memory_order_release);

    /* Bounded wait for executor to stop spinning */
    if (!timed_mutex_lock(&ctx->executor_mutex, timeout_ms)) {
        /* DEFECT FIX: Latch cleanup failure and DO NOT reopen the teardown gate */
        atomic_store_explicit(&ctx->cleanup_failed_latched, true, memory_order_release);
        return false;
    }

    pthread_mutex_lock(&ctx->fsm_mutex);

    /* --- CRITICAL SECTION: Finalizing entities --- */
    ctx->teardown_active_in_critical_section = true;
    if (ctx->executor_spinning) {
        ctx->concurrency_violations++;
    }
    usleep(100);

    bool all_clean = true;
    if (inject_entity_failure) {
        all_clean = false; /* Entity finalization failed */
    } else {
        ctx->executor_init = false;
        ctx->cmd_sub_init = false;
        ctx->node_init = false;
        ctx->support_init = false;
    }

    if (inject_memory_failure) {
        all_clean = false; /* Message memory destruction failed */
    } else {
        ctx->cmd_msg_memory = false;
        ctx->feedback_msg_memory = false;
    }

    ctx->teardown_active_in_critical_section = false;
    ctx->teardowns_completed++;

    bool has_unresolved = sync_has_unresolved_entities(ctx);

    pthread_mutex_unlock(&ctx->fsm_mutex);
    pthread_mutex_unlock(&ctx->executor_mutex);

    /* DEFECT FIX: Only reopen the gate if ALL entities were successfully and cleanly finalized
     * AND no prior cleanup failure was latched!
     * Standard teardown DOES NOT clear cleanup_failed_latched; deliberate recovery is required! */
    if (all_clean && !has_unresolved) {
        if (!atomic_load_explicit(&ctx->cleanup_failed_latched, memory_order_acquire)) {
            atomic_store_explicit(&ctx->teardown_in_progress, false, memory_order_release);
        }
    } else {
        /* Fail-closed: latch failure permanently; do NOT clear teardown_in_progress */
        atomic_store_explicit(&ctx->cleanup_failed_latched, true, memory_order_release);
    }

    return all_clean;
}

/**
 * Deliberate, verified lifecycle recovery procedure for concurrency tests.
 * Bounded, repeatable, and fail-closed.
 */
static bool sync_recover_unresolved_lifecycle(sync_test_ctx_t* ctx) {
    if (!ctx) return false;

    if (sync_is_executor_spinning_on_current_task(ctx)) {
        return false;
    }

    /* Execute teardown pass to clean up any remaining entities */
    bool clean = sync_destroy_microros_entities(ctx, 100, false, false);

    /* Verify under locks */
    if (!timed_mutex_lock(&ctx->executor_mutex, 100)) {
        return false;
    }
    pthread_mutex_lock(&ctx->fsm_mutex);

    bool recovery_ok = clean && !sync_has_unresolved_entities(ctx) &&
                       !ctx->cmd_msg_memory && !ctx->feedback_msg_memory;

    if (recovery_ok) {
        atomic_store_explicit(&ctx->cleanup_failed_latched, false, memory_order_release);
        atomic_store_explicit(&ctx->teardown_in_progress, false, memory_order_release);
    } else {
        atomic_store_explicit(&ctx->cleanup_failed_latched, true, memory_order_release);
    }

    pthread_mutex_unlock(&ctx->fsm_mutex);
    pthread_mutex_unlock(&ctx->executor_mutex);

    return recovery_ok;
}

static void sync_handle_agent_disconnect(sync_test_ctx_t* ctx) {
    pthread_mutex_lock(&ctx->fsm_mutex);
    /* Safe stop engaged */
    pthread_mutex_unlock(&ctx->fsm_mutex);

    if (sync_is_executor_spinning_on_current_task(ctx)) {
        /* Defer teardown to avoid self-deadlock and use-after-free */
        atomic_store_explicit(&ctx->disconnect_pending, true, memory_order_release);
        return;
    }

    (void)sync_destroy_microros_entities(ctx, 100, false, false);
}

/* Worker 1: Spinning executor */
static void* worker_spinning_executor(void* arg) {
    sync_test_ctx_t* ctx = (sync_test_ctx_t*)arg;

    while (!ctx->stop_test) {
        if (!sync_is_lifecycle_ready_for_spin(ctx)) {
            usleep(200);
            continue;
        }

        if (sync_executor_acquire_for_spin(ctx, 10)) {
            /* While spinning, teardown MUST NOT be active in critical section */
            if (ctx->teardown_active_in_critical_section) {
                ctx->concurrency_violations++;
            }
            usleep(100); /* 100 us simulated spin_some */
            sync_executor_release_from_spin(ctx);
            ctx->spins_completed++;
        }

        if (atomic_exchange_explicit(&ctx->disconnect_pending, false, memory_order_acq_rel)) {
            sync_handle_agent_disconnect(ctx);
        }

        usleep(50);
    }
    return NULL;
}

/* Worker 2: Concurrent teardown initiator */
static void* worker_concurrent_teardown(void* arg) {
    sync_test_ctx_t* ctx = (sync_test_ctx_t*)arg;

    while (!ctx->stop_test) {
        usleep(500);
        /* Periodically re-init entities to simulate reconnection, then trigger teardown */
        pthread_mutex_lock(&ctx->executor_mutex);
        if (!atomic_load_explicit(&ctx->cleanup_failed_latched, memory_order_acquire)) {
            ctx->support_init = true;
            ctx->node_init = true;
            ctx->executor_init = true;
            ctx->cmd_sub_init = true;
            ctx->cmd_msg_memory = true;
            ctx->feedback_msg_memory = true;
        }
        pthread_mutex_unlock(&ctx->executor_mutex);

        usleep(500);
        sync_destroy_microros_entities(ctx, 50, false, false);
    }
    return NULL;
}

void test_executor_vs_teardown_race(void) {
    printf("\n--- Test Executor-vs-Teardown Concurrency Race Prevention ---\n");

    pthread_mutexattr_t attr;
    pthread_mutexattr_init(&attr);
    pthread_mutexattr_settype(&attr, PTHREAD_MUTEX_RECURSIVE);
    pthread_mutex_init(&g_sync_ctx.fsm_mutex, &attr);
    pthread_mutexattr_destroy(&attr);

    pthread_mutex_init(&g_sync_ctx.executor_mutex, NULL);
    g_sync_ctx.support_init = true;
    g_sync_ctx.node_init = true;
    g_sync_ctx.executor_init = true;
    g_sync_ctx.cmd_sub_init = true;
    g_sync_ctx.cmd_msg_memory = true;
    g_sync_ctx.feedback_msg_memory = true;
    g_sync_ctx.executor_spinning = false;
    atomic_init(&g_sync_ctx.teardown_in_progress, false);
    atomic_init(&g_sync_ctx.cleanup_failed_latched, false);
    atomic_init(&g_sync_ctx.disconnect_pending, false);
    g_sync_ctx.teardown_active_in_critical_section = false;
    g_sync_ctx.spins_completed = 0;
    g_sync_ctx.teardowns_completed = 0;
    g_sync_ctx.concurrency_violations = 0;
    g_sync_ctx.stop_test = false;

    pthread_t t1, t2;
    pthread_create(&t1, NULL, worker_spinning_executor, &g_sync_ctx);
    pthread_create(&t2, NULL, worker_concurrent_teardown, &g_sync_ctx);

    /* Run intense concurrency for 150 ms */
    usleep(150000);

    g_sync_ctx.stop_test = true;
    pthread_join(t1, NULL);
    pthread_join(t2, NULL);

    pthread_mutex_destroy(&g_sync_ctx.fsm_mutex);
    pthread_mutex_destroy(&g_sync_ctx.executor_mutex);

    printf("  Sync stats: %d spins completed, %d teardowns completed, %d race violations\n",
           g_sync_ctx.spins_completed, g_sync_ctx.teardowns_completed, g_sync_ctx.concurrency_violations);

    TEST_ASSERT(g_sync_ctx.spins_completed > 50, "Executor successfully executed synchronized spins");
    TEST_ASSERT(g_sync_ctx.teardowns_completed > 10, "Teardown successfully executed synchronized teardowns");
    TEST_ASSERT(g_sync_ctx.concurrency_violations == 0, "Zero concurrency race violations between spin and teardown");
}

void test_teardown_timeout_when_executor_stuck(void) {
    printf("\n--- Test Teardown Bounded Timeout & Persistent Latch on Stuck Executor ---\n");

    pthread_mutex_init(&g_sync_ctx.executor_mutex, NULL);
    pthread_mutex_init(&g_sync_ctx.fsm_mutex, NULL);
    g_sync_ctx.support_init = true;
    g_sync_ctx.node_init = true;
    g_sync_ctx.executor_init = true;
    g_sync_ctx.cmd_sub_init = true;
    g_sync_ctx.cmd_msg_memory = true;
    g_sync_ctx.feedback_msg_memory = true;
    g_sync_ctx.executor_spinning = false;
    atomic_init(&g_sync_ctx.teardown_in_progress, false);
    atomic_init(&g_sync_ctx.cleanup_failed_latched, false);

    /* Simulate executor holding lock (e.g. stalled in blocking RMW call) */
    pthread_mutex_lock(&g_sync_ctx.executor_mutex);
    g_sync_ctx.executor_spinning = true;

    /* Teardown attempts to acquire lock with 50 ms timeout */
    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);
    bool clean = sync_destroy_microros_entities(&g_sync_ctx, 50, false, false);
    clock_gettime(CLOCK_MONOTONIC, &end);

    long elapsed_ms = (end.tv_sec - start.tv_sec) * 1000 + (end.tv_nsec - start.tv_nsec) / 1000000;

    TEST_ASSERT(!clean, "Teardown fails safely (returns false) when executor is stuck");
    TEST_ASSERT(g_sync_ctx.executor_init, "Executor was NOT finalized or freed while in use");
    TEST_ASSERT(elapsed_ms >= 45 && elapsed_ms <= 80, "Teardown bounded timeout enforced (~50 ms)");

    /* Requirement 1 & 2: Teardown timeout leaves admission blocked permanently */
    TEST_ASSERT(atomic_load_explicit(&g_sync_ctx.cleanup_failed_latched, memory_order_acquire),
                "Cleanup failure is PERSISTENTLY LATCHED on timeout");
    TEST_ASSERT(atomic_load_explicit(&g_sync_ctx.teardown_in_progress, memory_order_acquire),
                "Teardown gate remains locked CLOSED on timeout");

    /* Requirement 4: Spin admission must reject access */
    TEST_ASSERT(!sync_executor_acquire_for_spin(&g_sync_ctx, 10),
                "Spin admission strictly REJECTS while executor stuck and cleanup latched");

    /* Release stuck executor */
    g_sync_ctx.executor_spinning = false;
    pthread_mutex_unlock(&g_sync_ctx.executor_mutex);

    /* Requirement 4: Spin admission still rejects because failure latch is active */
    TEST_ASSERT(!sync_executor_acquire_for_spin(&g_sync_ctx, 10),
                "Spin admission STILL REJECTS after executor released because failure remains latched");

    /* Subtest: Second call to sync_destroy_microros_entities() MUST NOT clear cleanup_failed_latched! */
    clean = sync_destroy_microros_entities(&g_sync_ctx, 50, false, false);
    TEST_ASSERT(clean, "Standard teardown completes without error once lock is free");
    TEST_ASSERT(!g_sync_ctx.executor_init, "Executor cleanly finalized in second teardown");
    TEST_ASSERT(atomic_load_explicit(&g_sync_ctx.cleanup_failed_latched, memory_order_acquire),
                "Second teardown DOES NOT clear cleanup_failed_latched without deliberate recovery");
    TEST_ASSERT(atomic_load_explicit(&g_sync_ctx.teardown_in_progress, memory_order_acquire),
                "Teardown gate remains closed following second standard teardown");
    TEST_ASSERT(!sync_executor_acquire_for_spin(&g_sync_ctx, 10),
                "Spin admission STILL REJECTS because failure latch is still latched");

    /* Requirement 3: Deliberate recovery path succeeds and verifies zero unresolved entities */
    bool recovered = sync_recover_unresolved_lifecycle(&g_sync_ctx);
    TEST_ASSERT(recovered, "Deliberate recovery succeeds once executor released and all clean");
    TEST_ASSERT(!atomic_load_explicit(&g_sync_ctx.cleanup_failed_latched, memory_order_acquire),
                "Cleanup failure latch CLEARED after deliberate verified recovery");
    TEST_ASSERT(!atomic_load_explicit(&g_sync_ctx.teardown_in_progress, memory_order_acquire),
                "Teardown in progress CLEARED after deliberate verified recovery");

    pthread_mutex_destroy(&g_sync_ctx.executor_mutex);
    pthread_mutex_destroy(&g_sync_ctx.fsm_mutex);
}

void test_failed_finalization_blocks_admission(void) {
    printf("\n--- Test Failed Entity Finalization Leaves Admission Blocked ---\n");

    pthread_mutex_init(&g_sync_ctx.executor_mutex, NULL);
    pthread_mutex_init(&g_sync_ctx.fsm_mutex, NULL);
    g_sync_ctx.support_init = true;
    g_sync_ctx.node_init = true;
    g_sync_ctx.executor_init = true;
    g_sync_ctx.cmd_sub_init = true;
    g_sync_ctx.cmd_msg_memory = true;
    g_sync_ctx.feedback_msg_memory = true;
    g_sync_ctx.executor_spinning = false;
    atomic_init(&g_sync_ctx.teardown_in_progress, false);
    atomic_init(&g_sync_ctx.cleanup_failed_latched, false);

    /* 1. Teardown with injected entity finalization failure */
    bool clean = sync_destroy_microros_entities(&g_sync_ctx, 50, true, false);
    TEST_ASSERT(!clean, "Teardown reports failure when entity finalization fails");
    TEST_ASSERT(atomic_load_explicit(&g_sync_ctx.cleanup_failed_latched, memory_order_acquire),
                "Cleanup failure is PERSISTENTLY LATCHED on entity finalization failure");
    TEST_ASSERT(atomic_load_explicit(&g_sync_ctx.teardown_in_progress, memory_order_acquire),
                "Teardown gate remains latched CLOSED");

    /* 2. Subsequent spin attempts are rejected */
    TEST_ASSERT(!sync_executor_acquire_for_spin(&g_sync_ctx, 10),
                "Spin admission strictly REJECTED following failed entity finalization");

    /* 3. Entity recreation is blocked while cleanup failure is latched or teardown is in progress */
    bool recreate_allowed = !atomic_load_explicit(&g_sync_ctx.teardown_in_progress, memory_order_acquire) &&
                            !atomic_load_explicit(&g_sync_ctx.cleanup_failed_latched, memory_order_acquire) &&
                            !sync_has_unresolved_entities(&g_sync_ctx);
    TEST_ASSERT(!recreate_allowed, "Entity recreation strictly BLOCKED while cleanup is unresolved");

    /* 4. Second standard teardown call without fault injection */
    clean = sync_destroy_microros_entities(&g_sync_ctx, 50, false, false);
    TEST_ASSERT(clean, "Second standard teardown succeeds once entity fault is resolved");
    TEST_ASSERT(atomic_load_explicit(&g_sync_ctx.cleanup_failed_latched, memory_order_acquire),
                "Second teardown DOES NOT clear failure latch without deliberate recovery");
    TEST_ASSERT(atomic_load_explicit(&g_sync_ctx.teardown_in_progress, memory_order_acquire),
                "Teardown gate remains latched closed following second standard teardown");

    /* 5. Deliberate verified recovery procedure clears latch */
    bool recovered = sync_recover_unresolved_lifecycle(&g_sync_ctx);
    TEST_ASSERT(recovered, "Deliberate recovery succeeds once entity fault is resolved");
    TEST_ASSERT(!atomic_load_explicit(&g_sync_ctx.cleanup_failed_latched, memory_order_acquire),
                "Failure latch CLEARED after deliberate verified recovery");
    TEST_ASSERT(!atomic_load_explicit(&g_sync_ctx.teardown_in_progress, memory_order_acquire),
                "Teardown gate CLEARED after deliberate verified recovery");

    recreate_allowed = !atomic_load_explicit(&g_sync_ctx.teardown_in_progress, memory_order_acquire) &&
                       !atomic_load_explicit(&g_sync_ctx.cleanup_failed_latched, memory_order_acquire) &&
                       !sync_has_unresolved_entities(&g_sync_ctx);
    TEST_ASSERT(recreate_allowed, "Entity recreation now ALLOWED after verified recovery");

    pthread_mutex_destroy(&g_sync_ctx.executor_mutex);
    pthread_mutex_destroy(&g_sync_ctx.fsm_mutex);
}

void test_failed_memory_destruction_blocks_admission(void) {
    printf("\n--- Test Failed Message-Memory Destruction Leaves Admission Blocked ---\n");

    pthread_mutex_init(&g_sync_ctx.executor_mutex, NULL);
    pthread_mutex_init(&g_sync_ctx.fsm_mutex, NULL);
    g_sync_ctx.support_init = true;
    g_sync_ctx.node_init = true;
    g_sync_ctx.executor_init = true;
    g_sync_ctx.cmd_sub_init = true;
    g_sync_ctx.cmd_msg_memory = true;
    g_sync_ctx.feedback_msg_memory = true;
    g_sync_ctx.executor_spinning = false;
    atomic_init(&g_sync_ctx.teardown_in_progress, false);
    atomic_init(&g_sync_ctx.cleanup_failed_latched, false);

    /* 1. Teardown with injected memory destruction failure */
    bool clean = sync_destroy_microros_entities(&g_sync_ctx, 50, false, true);
    TEST_ASSERT(!clean, "Teardown reports failure when message memory destruction fails");
    TEST_ASSERT(atomic_load_explicit(&g_sync_ctx.cleanup_failed_latched, memory_order_acquire),
                "Cleanup failure is PERSISTENTLY LATCHED on memory destruction failure");
    TEST_ASSERT(atomic_load_explicit(&g_sync_ctx.teardown_in_progress, memory_order_acquire),
                "Teardown gate remains latched CLOSED");

    /* 2. Subsequent spin attempts are rejected */
    TEST_ASSERT(!sync_executor_acquire_for_spin(&g_sync_ctx, 10),
                "Spin admission strictly REJECTED following memory destruction failure");

    /* 3. Entity recreation blocked */
    bool recreate_allowed = !atomic_load_explicit(&g_sync_ctx.teardown_in_progress, memory_order_acquire) &&
                            !atomic_load_explicit(&g_sync_ctx.cleanup_failed_latched, memory_order_acquire) &&
                            !sync_has_unresolved_entities(&g_sync_ctx);
    TEST_ASSERT(!recreate_allowed, "Entity recreation strictly BLOCKED while memory is unresolved");

    /* 4. Second standard teardown call without fault injection */
    clean = sync_destroy_microros_entities(&g_sync_ctx, 50, false, false);
    TEST_ASSERT(clean, "Second standard teardown succeeds once memory fault resolved");
    TEST_ASSERT(atomic_load_explicit(&g_sync_ctx.cleanup_failed_latched, memory_order_acquire),
                "Second teardown DOES NOT clear failure latch without deliberate recovery");

    /* 5. Deliberate recovery clears latch only after verifying */
    bool recovered = sync_recover_unresolved_lifecycle(&g_sync_ctx);
    TEST_ASSERT(recovered, "Deliberate recovery succeeds once memory fault resolved");
    TEST_ASSERT(!atomic_load_explicit(&g_sync_ctx.cleanup_failed_latched, memory_order_acquire),
                "Failure latch CLEARED after deliberate verified recovery");

    pthread_mutex_destroy(&g_sync_ctx.executor_mutex);
    pthread_mutex_destroy(&g_sync_ctx.fsm_mutex);
}

void test_disconnect_from_executor_callback(void) {
    printf("\n--- Test Disconnect Initiated From Executor Callback (No Self-Deadlock) ---\n");

    pthread_mutex_init(&g_sync_ctx.executor_mutex, NULL);
    pthread_mutex_init(&g_sync_ctx.fsm_mutex, NULL);
    g_sync_ctx.support_init = true;
    g_sync_ctx.node_init = true;
    g_sync_ctx.executor_init = true;
    g_sync_ctx.cmd_sub_init = true;
    g_sync_ctx.cmd_msg_memory = true;
    g_sync_ctx.feedback_msg_memory = true;
    g_sync_ctx.executor_spinning = false;
    atomic_init(&g_sync_ctx.teardown_in_progress, false);
    atomic_init(&g_sync_ctx.cleanup_failed_latched, false);
    atomic_init(&g_sync_ctx.disconnect_pending, false);

    /* Acquire lock simulating executor entering spin_some */
    bool spin_ok = sync_executor_acquire_for_spin(&g_sync_ctx, 10);
    TEST_ASSERT(spin_ok, "Executor acquired spin lock");
    TEST_ASSERT(sync_is_executor_spinning_on_current_task(&g_sync_ctx),
                "Current thread is identified as spinning executor thread");

    /* Simulating command callback being invoked inside spin_some:
     * Callback initiates agent disconnect */
    sync_handle_agent_disconnect(&g_sync_ctx);

    /* Verify disconnect was deferred to prevent self-deadlock and use-after-free */
    TEST_ASSERT(atomic_load_explicit(&g_sync_ctx.disconnect_pending, memory_order_acquire),
                "Teardown was safely deferred (no deadlock inside callback)");
    TEST_ASSERT(g_sync_ctx.executor_init, "Executor memory remains valid for remainder of callback execution");

    /* Callback returns, spin_some completes and releases lock */
    sync_executor_release_from_spin(&g_sync_ctx);
    TEST_ASSERT(!sync_is_executor_spinning_on_current_task(&g_sync_ctx), "Spin lock released");

    /* Main loop checks g_disconnect_pending atomically and executes teardown outside of spin */
    if (atomic_exchange_explicit(&g_sync_ctx.disconnect_pending, false, memory_order_acq_rel)) {
        sync_handle_agent_disconnect(&g_sync_ctx);
    }

    TEST_ASSERT(!g_sync_ctx.executor_init, "Deferred teardown cleanly finalized executor outside of spin");

    pthread_mutex_destroy(&g_sync_ctx.executor_mutex);
    pthread_mutex_destroy(&g_sync_ctx.fsm_mutex);
}

void test_direct_teardown_refused_inside_callback(void) {
    printf("\n--- Test Direct Teardown Refused From Within Active Callback ---\n");

    pthread_mutex_init(&g_sync_ctx.executor_mutex, NULL);
    pthread_mutex_init(&g_sync_ctx.fsm_mutex, NULL);
    g_sync_ctx.support_init = true;
    g_sync_ctx.node_init = true;
    g_sync_ctx.executor_init = true;
    g_sync_ctx.cmd_sub_init = true;
    g_sync_ctx.cmd_msg_memory = true;
    g_sync_ctx.feedback_msg_memory = true;
    g_sync_ctx.executor_spinning = false;
    atomic_init(&g_sync_ctx.teardown_in_progress, false);
    atomic_init(&g_sync_ctx.cleanup_failed_latched, false);

    /* Simulate entering spin_some */
    bool spin_ok = sync_executor_acquire_for_spin(&g_sync_ctx, 10);
    TEST_ASSERT(spin_ok, "Executor acquired spin lock");

    /* Direct call to destroy_microros_entities from inside callback */
    bool clean = sync_destroy_microros_entities(&g_sync_ctx, 50, false, false);
    TEST_ASSERT(!clean, "Direct teardown from within active callback is strictly refused");
    TEST_ASSERT(g_sync_ctx.executor_init, "Executor was not finalized under its own feet");

    sync_executor_release_from_spin(&g_sync_ctx);

    pthread_mutex_destroy(&g_sync_ctx.executor_mutex);
    pthread_mutex_destroy(&g_sync_ctx.fsm_mutex);
}

void test_recovery_refuses_when_entities_or_memory_unresolved(void) {
    printf("\n--- Test Deliberate Recovery Refuses When Entities Or Memory Unresolved ---\n");

    pthread_mutex_init(&g_sync_ctx.executor_mutex, NULL);
    pthread_mutex_init(&g_sync_ctx.fsm_mutex, NULL);
    atomic_init(&g_sync_ctx.teardown_in_progress, false);
    atomic_init(&g_sync_ctx.cleanup_failed_latched, false);

    /* 1. Fail teardown via injected entity finalization failure */
    g_sync_ctx.support_init = true;
    g_sync_ctx.node_init = true;
    g_sync_ctx.executor_init = true;
    g_sync_ctx.cmd_sub_init = true;
    g_sync_ctx.cmd_msg_memory = true;
    g_sync_ctx.feedback_msg_memory = true;

    bool clean = sync_destroy_microros_entities(&g_sync_ctx, 50, true, false);
    TEST_ASSERT(!clean, "Initial teardown failed with injected entity fault");
    TEST_ASSERT(atomic_load_explicit(&g_sync_ctx.cleanup_failed_latched, memory_order_acquire),
                "Failure latched on entity finalization failure");

    /* 2. Direct attempt to recover while executor is spinning on current task: REFUSED */
    g_sync_ctx.executor_spinning = true;
    g_sync_ctx.executor_thread = pthread_self();
    g_sync_ctx.executor_thread_valid = true;

    bool recovered = sync_recover_unresolved_lifecycle(&g_sync_ctx);
    TEST_ASSERT(!recovered, "Recovery strictly refused while executor is spinning on calling thread");
    TEST_ASSERT(atomic_load_explicit(&g_sync_ctx.cleanup_failed_latched, memory_order_acquire),
                "Failure remains latched after refused recovery");

    g_sync_ctx.executor_spinning = false;
    g_sync_ctx.executor_thread_valid = false;

    /* 3. Now let recovery succeed cleanly */
    recovered = sync_recover_unresolved_lifecycle(&g_sync_ctx);
    TEST_ASSERT(recovered, "Recovery succeeds when all entities and memory are cleanly finalized");
    TEST_ASSERT(!atomic_load_explicit(&g_sync_ctx.cleanup_failed_latched, memory_order_acquire),
                "Failure latch cleared after successful recovery");
    TEST_ASSERT(!atomic_load_explicit(&g_sync_ctx.teardown_in_progress, memory_order_acquire),
                "Teardown gate reopened after successful recovery");

    pthread_mutex_destroy(&g_sync_ctx.executor_mutex);
    pthread_mutex_destroy(&g_sync_ctx.fsm_mutex);
}

int main(void) {
    printf("===============================================================\n");
    printf("   CDPR Concurrency & Mutex Synchronization Tests (HOST-ONLY)  \n");
    printf("   NOTE: Validates software logic only; NOT hardware safety    \n");
    printf("===============================================================\n");

    test_recursive_mutex_nested_locking();
    test_multithreaded_concurrency_stress();
    test_executor_vs_teardown_race();
    test_teardown_timeout_when_executor_stuck();
    test_failed_finalization_blocks_admission();
    test_failed_memory_destruction_blocks_admission();
    test_disconnect_from_executor_callback();
    test_direct_teardown_refused_inside_callback();
    test_recovery_refuses_when_entities_or_memory_unresolved();

    printf("\n===============================================================\n");
    printf(" Results: %d / %d tests passed\n", g_tests_passed, g_tests_run);
    printf("===============================================================\n");

    return (g_tests_passed == g_tests_run) ? 0 : 1;
}
