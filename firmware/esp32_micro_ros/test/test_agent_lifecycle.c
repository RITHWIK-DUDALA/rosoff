/**
 * Unit test suite for CDPR micro-ROS Agent Lifecycle, Failure Paths, and Entity Cleanup.
 *
 * NOTE: This is a HOST-BASED unit test suite.
 * It validates state machine transitions, lifecycle logic, failure recovery paths,
 * idempotence, and entity dependency ordering in simulation.
 * It DOES NOT represent physical hardware validation, physical STO, or physical drive testing.
 *
 * Verifies:
 * - Requirement 1: Checked finalization results and failure recording.
 * - Requirement 2: Preserving unresolved lifecycle state on finalization failure.
 * - Requirement 3: Explicit boolean handling for message memory destruction.
 * - Requirement 4: Respecting ROS entity dependency order (subs/pubs before node, node before support).
 * - Requirement 5: Executor spinning check preventing concurrent teardown.
 * - Requirement 6: Safe partial initialization and idempotent repeated teardown (no double-free).
 * - Requirement 7: Fail-closed transitions to STATE_FAULT on unresolved cleanup and creation refusal.
 */
#include <stdio.h>
#include <string.h>
#include <stdbool.h>
#include <stdint.h>
#include "../main/app_state.h"
#include "../main/servo_driver_interface.h"

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

/* Mock entity tracker matching main.c cdpr_entity_lifecycle_t */
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
} mock_lifecycle_t;

/* Counter tracking how many times each entity was destroyed */
typedef struct {
    int support_fini_count;
    int node_fini_count;
    int cmd_sub_fini_count;
    int ctrl_sub_fini_count;
    int feedback_pub_fini_count;
    int status_pub_fini_count;
    int feedback_valid_pub_fini_count;
    int cmd_msg_destroy_count;
    int feedback_msg_destroy_count;
    int executor_fini_count;
} fini_counters_t;

/* Fault injection configuration for finalization APIs */
typedef struct {
    bool fail_executor_fini;
    bool fail_cmd_msg_destroy;
    bool fail_feedback_msg_destroy;
    bool fail_cmd_sub_fini;
    bool fail_ctrl_sub_fini;
    bool fail_feedback_pub_fini;
    bool fail_status_pub_fini;
    bool fail_feedback_valid_pub_fini;
    bool fail_node_fini;
    bool fail_support_fini;
} fini_fault_injection_t;

static mock_lifecycle_t       g_mock_lifecycle;
static fini_counters_t        g_fini_counters;
static fini_fault_injection_t g_faults;
static bool                   g_mock_teardown_in_progress = false;
static bool                   g_mock_cleanup_failed_latched = false;

static inline bool mock_has_unresolved_entities(const mock_lifecycle_t* lc) {
    if (lc == NULL) return false;
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

static inline bool mock_is_lifecycle_ready_for_spin(const mock_lifecycle_t* lc) {
    if (lc == NULL) return false;
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

static bool mock_executor_acquire_for_spin(void) {
    if (g_mock_teardown_in_progress ||
        g_mock_cleanup_failed_latched ||
        !mock_is_lifecycle_ready_for_spin(&g_mock_lifecycle)) {
        return false;
    }
    g_mock_lifecycle.executor_spinning = true;
    return true;
}

static void mock_executor_release_from_spin(void) {
    g_mock_lifecycle.executor_spinning = false;
}

/**
 * Mock entity destructor replicating destroy_microros_entities() from main.c.
 * Respects:
 * - Active executor check (aborts if spinning).
 * - Exact return codes and simulated finalization failures.
 * - Preserving lifecycle flags when finalization fails.
 * - Strict entity dependency order (node requires all pubs/subs fini; support requires node fini).
 * - Returns true if all entities cleanly destroyed, false if unresolved.
 */
static bool mock_destroy_microros_entities(void) {
    if (g_mock_lifecycle.executor_spinning) {
        printf("    [MOCK TEARDOWN] Aborted: Executor is currently spinning!\n");
        g_mock_cleanup_failed_latched = true;
        g_mock_teardown_in_progress = true;
        return false;
    }

    g_mock_teardown_in_progress = true;
    bool all_clean = true;

    /* --- Stage 1: Executor Finalization --- */
    if (g_mock_lifecycle.executor_init) {
        if (g_faults.fail_executor_fini) {
            printf("    [MOCK TEARDOWN] Injected failure: rclc_executor_fini failed!\n");
            all_clean = false;
        } else {
            g_fini_counters.executor_fini_count++;
            g_mock_lifecycle.executor_init = false;
            g_mock_lifecycle.cmd_sub_in_executor = false;
            g_mock_lifecycle.ctrl_sub_in_executor = false;
        }
    }

    /* --- Stage 2: Dynamic Message Memory Destruction --- */
    if (g_mock_lifecycle.cmd_msg_memory) {
        if (g_faults.fail_cmd_msg_destroy) {
            printf("    [MOCK TEARDOWN] Injected failure: cmd_msg memory destruction returned false!\n");
            all_clean = false;
        } else {
            g_fini_counters.cmd_msg_destroy_count++;
            g_mock_lifecycle.cmd_msg_memory = false;
        }
    }

    if (g_mock_lifecycle.feedback_msg_memory) {
        if (g_faults.fail_feedback_msg_destroy) {
            printf("    [MOCK TEARDOWN] Injected failure: feedback_msg memory destruction returned false!\n");
            all_clean = false;
        } else {
            g_fini_counters.feedback_msg_destroy_count++;
            g_mock_lifecycle.feedback_msg_memory = false;
        }
    }

    /* --- Stage 3: Subscriptions and Publishers Finalization --- */
    if (g_mock_lifecycle.ctrl_sub_init) {
        if (g_faults.fail_ctrl_sub_fini) {
            printf("    [MOCK TEARDOWN] Injected failure: ctrl_sub finalization failed!\n");
            all_clean = false;
        } else {
            g_fini_counters.ctrl_sub_fini_count++;
            g_mock_lifecycle.ctrl_sub_init = false;
        }
    }

    if (g_mock_lifecycle.cmd_sub_init) {
        if (g_faults.fail_cmd_sub_fini) {
            printf("    [MOCK TEARDOWN] Injected failure: cmd_sub finalization failed!\n");
            all_clean = false;
        } else {
            g_fini_counters.cmd_sub_fini_count++;
            g_mock_lifecycle.cmd_sub_init = false;
        }
    }

    if (g_mock_lifecycle.feedback_valid_pub_init) {
        if (g_faults.fail_feedback_valid_pub_fini) {
            printf("    [MOCK TEARDOWN] Injected failure: feedback_valid_pub finalization failed!\n");
            all_clean = false;
        } else {
            g_fini_counters.feedback_valid_pub_fini_count++;
            g_mock_lifecycle.feedback_valid_pub_init = false;
        }
    }

    if (g_mock_lifecycle.status_pub_init) {
        if (g_faults.fail_status_pub_fini) {
            printf("    [MOCK TEARDOWN] Injected failure: status_pub finalization failed!\n");
            all_clean = false;
        } else {
            g_fini_counters.status_pub_fini_count++;
            g_mock_lifecycle.status_pub_init = false;
        }
    }

    if (g_mock_lifecycle.feedback_pub_init) {
        if (g_faults.fail_feedback_pub_fini) {
            printf("    [MOCK TEARDOWN] Injected failure: feedback_pub finalization failed!\n");
            all_clean = false;
        } else {
            g_fini_counters.feedback_pub_fini_count++;
            g_mock_lifecycle.feedback_pub_init = false;
        }
    }

    /* --- Stage 4: Node Finalization (Strict Dependency Check) --- */
    bool node_has_dependents = (
        g_mock_lifecycle.cmd_sub_init ||
        g_mock_lifecycle.ctrl_sub_init ||
        g_mock_lifecycle.feedback_pub_init ||
        g_mock_lifecycle.status_pub_init ||
        g_mock_lifecycle.feedback_valid_pub_init
    );

    if (g_mock_lifecycle.node_init) {
        if (node_has_dependents) {
            printf("    [MOCK TEARDOWN] Dependency violation: Cannot finalize rcl_node while dependent publishers or subscriptions remain active!\n");
            all_clean = false;
        } else if (g_faults.fail_node_fini) {
            printf("    [MOCK TEARDOWN] Injected failure: rcl_node_fini failed!\n");
            all_clean = false;
        } else {
            g_fini_counters.node_fini_count++;
            g_mock_lifecycle.node_init = false;
        }
    }

    /* --- Stage 5: Support Context Finalization (Strict Dependency Check) --- */
    if (g_mock_lifecycle.support_init) {
        if (g_mock_lifecycle.node_init) {
            printf("    [MOCK TEARDOWN] Dependency violation: Cannot finalize rclc_support while node remains initialized!\n");
            all_clean = false;
        } else if (g_faults.fail_support_fini) {
            printf("    [MOCK TEARDOWN] Injected failure: rclc_support_fini failed!\n");
            all_clean = false;
        } else {
            g_fini_counters.support_fini_count++;
            g_mock_lifecycle.support_init = false;
        }
    }

    if (all_clean && !mock_has_unresolved_entities(&g_mock_lifecycle)) {
        if (!g_mock_cleanup_failed_latched) {
            g_mock_teardown_in_progress = false;
        }
    } else {
        g_mock_cleanup_failed_latched = true;
        /* Do NOT clear g_mock_teardown_in_progress */
    }

    return all_clean;
}

/**
 * Simulates deliberate, verified recovery procedure cdpr_recover_unresolved_lifecycle().
 */
static bool mock_recover_unresolved_lifecycle(void) {
    if (g_mock_lifecycle.executor_spinning) {
        printf("    [MOCK RECOVERY] Refused: Executor is spinning!\n");
        return false;
    }

    bool clean = mock_destroy_microros_entities();

    bool recovery_ok = clean && !mock_has_unresolved_entities(&g_mock_lifecycle) &&
                       !g_mock_lifecycle.cmd_msg_memory && !g_mock_lifecycle.feedback_msg_memory;

    if (recovery_ok) {
        g_mock_cleanup_failed_latched = false;
        g_mock_teardown_in_progress = false;
        printf("    [MOCK RECOVERY] Deliberate recovery verified safe: All entities resolved.\n");
    } else {
        g_mock_cleanup_failed_latched = true;
        printf("    [MOCK RECOVERY] Recovery failed: Unresolved entities remain.\n");
    }

    return recovery_ok;
}

/**
 * Simulates create_microros_entities() with failure injection at step 'fail_at_step' (1..12).
 * Refuses creation if any unresolved entity exists or cleanup failure is latched.
 * Returns true if successful, false on injected failure.
 */
static bool mock_create_microros_entities(int fail_at_step) {
    if (g_mock_teardown_in_progress || g_mock_cleanup_failed_latched || mock_has_unresolved_entities(&g_mock_lifecycle)) {
        printf("    [MOCK CREATE] Refused: Teardown in progress, cleanup failure latched, or unresolved entities remain!\n");
        return false;
    }

    memset(&g_mock_lifecycle, 0, sizeof(g_mock_lifecycle));

    /* Step 1: Support */
    if (fail_at_step == 1) { (void)mock_destroy_microros_entities(); return false; }
    g_mock_lifecycle.support_init = true;

    /* Step 2: Node */
    if (fail_at_step == 2) { (void)mock_destroy_microros_entities(); return false; }
    g_mock_lifecycle.node_init = true;

    /* Step 3: Cmd Sub */
    if (fail_at_step == 3) { (void)mock_destroy_microros_entities(); return false; }
    g_mock_lifecycle.cmd_sub_init = true;

    /* Step 4: Ctrl Sub */
    if (fail_at_step == 4) { (void)mock_destroy_microros_entities(); return false; }
    g_mock_lifecycle.ctrl_sub_init = true;

    /* Step 5: Feedback Pub */
    if (fail_at_step == 5) { (void)mock_destroy_microros_entities(); return false; }
    g_mock_lifecycle.feedback_pub_init = true;

    /* Step 6: Status Pub */
    if (fail_at_step == 6) { (void)mock_destroy_microros_entities(); return false; }
    g_mock_lifecycle.status_pub_init = true;

    /* Step 7: Feedback Valid Pub */
    if (fail_at_step == 7) { (void)mock_destroy_microros_entities(); return false; }
    g_mock_lifecycle.feedback_valid_pub_init = true;

    /* Step 8: Cmd Msg Memory */
    if (fail_at_step == 8) { (void)mock_destroy_microros_entities(); return false; }
    g_mock_lifecycle.cmd_msg_memory = true;

    /* Step 9: Feedback Msg Memory */
    if (fail_at_step == 9) { (void)mock_destroy_microros_entities(); return false; }
    g_mock_lifecycle.feedback_msg_memory = true;

    /* Step 10: Executor Init */
    if (fail_at_step == 10) { (void)mock_destroy_microros_entities(); return false; }
    g_mock_lifecycle.executor_init = true;

    /* Step 11: Cmd Sub in Executor */
    if (fail_at_step == 11) { (void)mock_destroy_microros_entities(); return false; }
    g_mock_lifecycle.cmd_sub_in_executor = true;

    /* Step 12: Ctrl Sub in Executor */
    if (fail_at_step == 12) { (void)mock_destroy_microros_entities(); return false; }
    g_mock_lifecycle.ctrl_sub_in_executor = true;

    return true;
}

void test_entity_creation_failure_paths(void) {
    printf("\n--- Test Entity Initialization Failures & Granular Cleanup ---\n");
    memset(&g_faults, 0, sizeof(g_faults));

    for (int fail_step = 1; fail_step <= 12; fail_step++) {
        memset(&g_fini_counters, 0, sizeof(g_fini_counters));
        bool ok = mock_create_microros_entities(fail_step);
        TEST_ASSERT(!ok, "Creation fails when step fails");

        /* Verify that only entities initialized prior to fail_step were finalized */
        TEST_ASSERT(g_fini_counters.support_fini_count == (fail_step > 1 ? 1 : 0),
                    "Support finalized exactly once if created");
        TEST_ASSERT(g_fini_counters.node_fini_count == (fail_step > 2 ? 1 : 0),
                    "Node finalized exactly once if created");
        TEST_ASSERT(g_fini_counters.cmd_sub_fini_count == (fail_step > 3 ? 1 : 0),
                    "Cmd sub finalized exactly once if created");
        TEST_ASSERT(g_fini_counters.ctrl_sub_fini_count == (fail_step > 4 ? 1 : 0),
                    "Ctrl sub finalized exactly once if created");
        TEST_ASSERT(g_fini_counters.feedback_pub_fini_count == (fail_step > 5 ? 1 : 0),
                    "Feedback pub finalized exactly once if created");
        TEST_ASSERT(g_fini_counters.status_pub_fini_count == (fail_step > 6 ? 1 : 0),
                    "Status pub finalized exactly once if created");
        TEST_ASSERT(g_fini_counters.feedback_valid_pub_fini_count == (fail_step > 7 ? 1 : 0),
                    "Feedback valid pub finalized exactly once if created");
        TEST_ASSERT(g_fini_counters.cmd_msg_destroy_count == (fail_step > 8 ? 1 : 0),
                    "Cmd msg memory destroyed exactly once if allocated");
        TEST_ASSERT(g_fini_counters.feedback_msg_destroy_count == (fail_step > 9 ? 1 : 0),
                    "Feedback msg memory destroyed exactly once if allocated");
        TEST_ASSERT(g_fini_counters.executor_fini_count == (fail_step > 10 ? 1 : 0),
                    "Executor finalized exactly once if created");

        /* Verify idempotence: calling teardown a second time does nothing */
        bool second_clean = mock_destroy_microros_entities();
        TEST_ASSERT(second_clean, "Second destroy on cleanly torn down state returns true");
        TEST_ASSERT(g_fini_counters.support_fini_count == (fail_step > 1 ? 1 : 0),
                    "Second destroy does not re-finalize support (no double-free)");
        TEST_ASSERT(g_fini_counters.executor_fini_count == (fail_step > 10 ? 1 : 0),
                    "Second destroy does not re-finalize executor");
    }

    /* Test full successful creation and teardown */
    memset(&g_fini_counters, 0, sizeof(g_fini_counters));
    bool ok = mock_create_microros_entities(0); /* 0 = succeed all */
    TEST_ASSERT(ok, "Complete creation succeeds");
    bool clean = mock_destroy_microros_entities();
    TEST_ASSERT(clean, "Full teardown returns true (all clean)");
    TEST_ASSERT(g_fini_counters.support_fini_count == 1, "Full teardown finalized support");
    TEST_ASSERT(g_fini_counters.node_fini_count == 1, "Full teardown finalized node");
    TEST_ASSERT(g_fini_counters.feedback_valid_pub_fini_count == 1, "Full teardown finalized feedback_valid pub");
    TEST_ASSERT(g_fini_counters.executor_fini_count == 1, "Full teardown finalized executor");
    TEST_ASSERT(g_fini_counters.cmd_msg_destroy_count == 1, "Full teardown freed cmd msg memory");
    TEST_ASSERT(g_fini_counters.feedback_msg_destroy_count == 1, "Full teardown freed feedback msg memory");
}

void test_simulated_teardown_failures(void) {
    printf("\n--- Test Simulated Finalization Failures & Dependency Enforcement ---\n");

    /* --- Subcase A: Subscription finalization failure prevents node and support fini --- */
    {
        memset(&g_mock_lifecycle, 0, sizeof(g_mock_lifecycle));
        memset(&g_fini_counters, 0, sizeof(g_fini_counters));
        memset(&g_faults, 0, sizeof(g_faults));

        bool created = mock_create_microros_entities(0);
        TEST_ASSERT(created, "Subcase A: Entities initialized");

        /* Inject failure on cmd_sub_fini */
        g_faults.fail_cmd_sub_fini = true;

        bool clean = mock_destroy_microros_entities();
        TEST_ASSERT(!clean, "Subcase A: Teardown reports failure when cmd_sub_fini fails");
        TEST_ASSERT(g_mock_cleanup_failed_latched, "Subcase A: Cleanup failure is PERSISTENTLY LATCHED");
        TEST_ASSERT(g_mock_teardown_in_progress, "Subcase A: Teardown gate remains locked CLOSED");
        TEST_ASSERT(!mock_executor_acquire_for_spin(),
                    "Subcase A: Spin admission strictly REJECTED following failed entity teardown");
        TEST_ASSERT(g_mock_lifecycle.cmd_sub_init, "Subcase A: cmd_sub_init remains true after failed fini");
        TEST_ASSERT(g_fini_counters.node_fini_count == 0,
                    "Subcase A: node_fini SKIPPED due to active dependent cmd_sub (dependency check)");
        TEST_ASSERT(g_mock_lifecycle.node_init, "Subcase A: node_init remains true");
        TEST_ASSERT(g_fini_counters.support_fini_count == 0,
                    "Subcase A: support_fini SKIPPED due to active node (dependency check)");
        TEST_ASSERT(g_mock_lifecycle.support_init, "Subcase A: support_init remains true");
        TEST_ASSERT(mock_has_unresolved_entities(&g_mock_lifecycle),
                    "Subcase A: Unresolved entities detected");

        /* Attempting to recreate entities while unresolved MUST be refused */
        bool recreate_ok = mock_create_microros_entities(0);
        TEST_ASSERT(!recreate_ok, "Subcase A: Creation refused over unresolved entities / failure latch");

        /* Second teardown pass without fault: clean entities, but failure remains latched */
        g_faults.fail_cmd_sub_fini = false;
        clean = mock_destroy_microros_entities();
        TEST_ASSERT(clean, "Subcase A: Second teardown pass finishes entity cleanup");
        TEST_ASSERT(g_mock_cleanup_failed_latched, "Subcase A: Second teardown call DOES NOT clear failure latch without recovery procedure");
        TEST_ASSERT(!mock_executor_acquire_for_spin(), "Subcase A: Spin admission STILL REJECTED after second teardown call");
        TEST_ASSERT(!mock_create_microros_entities(0), "Subcase A: Recreation STILL BLOCKED after second teardown call");

        /* Deliberate verified recovery procedure */
        bool recovered = mock_recover_unresolved_lifecycle();
        TEST_ASSERT(recovered, "Subcase A Recovery: Deliberate recovery succeeds once entities confirmed resolved");
        TEST_ASSERT(!g_mock_cleanup_failed_latched, "Subcase A Recovery: Failure latch cleared ONLY by deliberate recovery");
        TEST_ASSERT(!g_mock_teardown_in_progress, "Subcase A Recovery: Teardown gate cleared ONLY by deliberate recovery");
        TEST_ASSERT(!mock_has_unresolved_entities(&g_mock_lifecycle),
                    "Subcase A Recovery: No unresolved entities remain");
        TEST_ASSERT(g_fini_counters.node_fini_count == 1,
                    "Subcase A Recovery: Node finalized now that dependent is clean");
        TEST_ASSERT(g_fini_counters.support_fini_count == 1,
                    "Subcase A Recovery: Support finalized now that node is clean");

        /* Now recreation succeeds */
        recreate_ok = mock_create_microros_entities(0);
        TEST_ASSERT(recreate_ok, "Subcase A Recovery: Creation now succeeds");
        TEST_ASSERT(mock_executor_acquire_for_spin(),
                    "Subcase A Recovery: Spin admission now allowed when fully initialized");
        mock_executor_release_from_spin();
        (void)mock_destroy_microros_entities();
    }

    /* --- Subcase B: Dynamic message memory destruction failure --- */
    {
        memset(&g_mock_lifecycle, 0, sizeof(g_mock_lifecycle));
        memset(&g_fini_counters, 0, sizeof(g_fini_counters));
        memset(&g_faults, 0, sizeof(g_faults));

        bool created = mock_create_microros_entities(0);
        TEST_ASSERT(created, "Subcase B: Entities initialized");

        /* Inject failure on feedback_msg memory destruction */
        g_faults.fail_feedback_msg_destroy = true;

        bool clean = mock_destroy_microros_entities();
        TEST_ASSERT(!clean, "Subcase B: Teardown reports failure when message memory destruction fails");
        TEST_ASSERT(g_mock_cleanup_failed_latched, "Subcase B: Cleanup failure is PERSISTENTLY LATCHED");
        TEST_ASSERT(g_mock_teardown_in_progress, "Subcase B: Teardown gate remains locked CLOSED");
        TEST_ASSERT(!mock_executor_acquire_for_spin(),
                    "Subcase B: Spin admission rejected on message memory destruction failure");
        TEST_ASSERT(g_mock_lifecycle.feedback_msg_memory,
                    "Subcase B: feedback_msg_memory flag preserved (not falsely marked freed)");
        TEST_ASSERT(mock_has_unresolved_entities(&g_mock_lifecycle),
                    "Subcase B: Unresolved entity detected due to leaked message memory");

        /* Attempt recreation fails */
        TEST_ASSERT(!mock_create_microros_entities(0),
                    "Subcase B: Creation refused while message memory is unresolved");

        /* Second teardown without fault: cleans memory, but failure remains latched */
        g_faults.fail_feedback_msg_destroy = false;
        clean = mock_destroy_microros_entities();
        TEST_ASSERT(clean, "Subcase B: Second teardown resolves message memory");
        TEST_ASSERT(g_mock_cleanup_failed_latched, "Subcase B: Second teardown DOES NOT clear failure latch without recovery procedure");
        TEST_ASSERT(!mock_executor_acquire_for_spin(), "Subcase B: Spin admission STILL REJECTED after second teardown");
        TEST_ASSERT(!mock_create_microros_entities(0), "Subcase B: Recreation STILL BLOCKED after second teardown");

        /* Deliberate verified recovery procedure */
        bool recovered = mock_recover_unresolved_lifecycle();
        TEST_ASSERT(recovered, "Subcase B Recovery: Deliberate recovery succeeds once memory confirmed resolved");
        TEST_ASSERT(!g_mock_cleanup_failed_latched, "Subcase B Recovery: Failure latch cleared ONLY by deliberate recovery");
        TEST_ASSERT(!g_mock_teardown_in_progress, "Subcase B Recovery: Teardown gate cleared ONLY by deliberate recovery");
        TEST_ASSERT(!g_mock_lifecycle.feedback_msg_memory, "Subcase B Recovery: feedback_msg_memory cleared");
    }

    /* --- Subcase C: Node finalization failure prevents support fini --- */
    {
        memset(&g_mock_lifecycle, 0, sizeof(g_mock_lifecycle));
        memset(&g_fini_counters, 0, sizeof(g_fini_counters));
        memset(&g_faults, 0, sizeof(g_faults));

        bool created = mock_create_microros_entities(0);
        TEST_ASSERT(created, "Subcase C: Entities initialized");

        /* Inject failure on node_fini */
        g_faults.fail_node_fini = true;

        bool clean = mock_destroy_microros_entities();
        TEST_ASSERT(!clean, "Subcase C: Teardown reports failure when node_fini fails");
        TEST_ASSERT(g_mock_cleanup_failed_latched, "Subcase C: Cleanup failure is PERSISTENTLY LATCHED");
        TEST_ASSERT(g_mock_teardown_in_progress, "Subcase C: Teardown gate remains locked CLOSED");
        TEST_ASSERT(!mock_executor_acquire_for_spin(),
                    "Subcase C: Spin admission rejected on node_fini failure");
        TEST_ASSERT(g_mock_lifecycle.node_init, "Subcase C: node_init remains true");
        TEST_ASSERT(g_fini_counters.support_fini_count == 0,
                    "Subcase C: support_fini SKIPPED because node is still active (dependency check)");
        TEST_ASSERT(g_mock_lifecycle.support_init, "Subcase C: support_init remains true");

        /* Creation refused */
        TEST_ASSERT(!mock_create_microros_entities(0),
                    "Subcase C: Creation refused while node is unresolved");

        /* Second teardown without fault: completes node/support fini, but failure remains latched */
        g_faults.fail_node_fini = false;
        clean = mock_destroy_microros_entities();
        TEST_ASSERT(clean, "Subcase C: Second teardown completes entity finalization");
        TEST_ASSERT(g_mock_cleanup_failed_latched, "Subcase C: Second teardown DOES NOT clear failure latch without recovery procedure");
        TEST_ASSERT(!mock_executor_acquire_for_spin(), "Subcase C: Spin admission STILL REJECTED after second teardown");
        TEST_ASSERT(!mock_create_microros_entities(0), "Subcase C: Recreation STILL BLOCKED after second teardown");

        /* Deliberate verified recovery procedure */
        bool recovered = mock_recover_unresolved_lifecycle();
        TEST_ASSERT(recovered, "Subcase C Recovery: Deliberate recovery succeeds once node/support confirmed resolved");
        TEST_ASSERT(!g_mock_cleanup_failed_latched, "Subcase C Recovery: Failure latch cleared ONLY by deliberate recovery");
        TEST_ASSERT(!g_mock_teardown_in_progress, "Subcase C Recovery: Teardown gate cleared ONLY by deliberate recovery");
        TEST_ASSERT(g_fini_counters.node_fini_count == 1, "Subcase C Recovery: Node finalized");
        TEST_ASSERT(g_fini_counters.support_fini_count == 1, "Subcase C Recovery: Support finalized");
    }
}

void test_executor_spinning_guard(void) {
    printf("\n--- Test Active Executor Spinning Guard ---\n");
    memset(&g_mock_lifecycle, 0, sizeof(g_mock_lifecycle));
    memset(&g_fini_counters, 0, sizeof(g_fini_counters));
    memset(&g_faults, 0, sizeof(g_faults));

    bool created = mock_create_microros_entities(0);
    TEST_ASSERT(created, "Entities initialized");

    /* Mark executor as currently spinning (e.g. concurrent callback or spin_some running) */
    g_mock_lifecycle.executor_spinning = true;

    bool clean = mock_destroy_microros_entities();
    TEST_ASSERT(!clean, "Teardown strictly refused when executor is spinning");
    TEST_ASSERT(g_mock_cleanup_failed_latched, "Teardown refusal latches cleanup failure");
    TEST_ASSERT(g_mock_teardown_in_progress, "Teardown gate remains closed");
    TEST_ASSERT(g_fini_counters.executor_fini_count == 0, "Executor fini was not called");
    TEST_ASSERT(g_fini_counters.support_fini_count == 0, "Support fini was not called");
    TEST_ASSERT(g_mock_lifecycle.executor_init, "Executor remains initialized");

    /* Once spinning finishes, release spinning flag */
    g_mock_lifecycle.executor_spinning = false;

    /* Spin admission STILL rejected because failure remains latched */
    TEST_ASSERT(!mock_executor_acquire_for_spin(),
                "Spin admission STILL REJECTED after executor stopped spinning because failure latch is active");

    /* Second teardown call cleans entities, but failure remains latched */
    clean = mock_destroy_microros_entities();
    TEST_ASSERT(clean, "Second teardown completes entity finalization");
    TEST_ASSERT(g_mock_cleanup_failed_latched, "Second teardown DOES NOT clear failure latch without recovery procedure");
    TEST_ASSERT(!mock_executor_acquire_for_spin(), "Spin admission STILL REJECTED after second teardown");

    /* Deliberate verified recovery procedure */
    bool recovered = mock_recover_unresolved_lifecycle();
    TEST_ASSERT(recovered, "Deliberate recovery procedure succeeds once executor stops spinning");
    TEST_ASSERT(!g_mock_cleanup_failed_latched, "Failure latch cleared ONLY by deliberate recovery");
    TEST_ASSERT(!g_mock_teardown_in_progress, "Teardown in progress cleared ONLY by deliberate recovery");
    TEST_ASSERT(g_fini_counters.executor_fini_count == 1, "Executor finalized cleanly");
}

/* Agent loss simulator matching fsm_handle_agent_disconnect() logic in main.c */
static void simulate_agent_disconnect(
    cdpr_firmware_state_t* state,
    bool* agent_connected,
    cdpr_servo_status_t* servo,
    bool* teardown_called,
    bool* safe_stop_engaged_before_teardown,
    bool simulate_teardown_failure
) {
    *agent_connected = false;

    if (*state == STATE_MOTION_ENABLED) {
        /* Fail-closed safety: clamp velocities and safe stop BEFORE teardown */
        cdpr_servo_emergency_safe_stop(servo);
        *safe_stop_engaged_before_teardown = true;
        *state = STATE_SAFE_STOP;
    }

    /* Teardown micro-ROS entities */
    *teardown_called = true;
    bool teardown_clean = !simulate_teardown_failure;

    if (!teardown_clean) {
        /* Unresolved teardown forces STATE_FAULT (Fail-closed) */
        *state = STATE_FAULT;
    } else {
        /* Clean teardown transitions back to WAITING_FOR_AGENT if legal */
        if (cdpr_is_valid_transition(*state, STATE_WAITING_FOR_AGENT)) {
            *state = STATE_WAITING_FOR_AGENT;
        }
    }
}

void test_agent_loss_across_fsm_states(void) {
    printf("\n--- Test Agent Loss Handling Across All FSM States ---\n");

    cdpr_firmware_state_t states_to_test[] = {
        STATE_BOOT,
        STATE_INITIALIZING,
        STATE_WAITING_FOR_AGENT,
        STATE_CONNECTED,
        STATE_DRIVE_STATUS_CHECK,
        STATE_READY,
        STATE_MOTION_ENABLED,
        STATE_SAFE_STOP,
        STATE_FAULT
    };

    /* Part 1: Clean teardown path */
    for (size_t i = 0; i < sizeof(states_to_test)/sizeof(states_to_test[0]); i++) {
        cdpr_firmware_state_t st = states_to_test[i];
        bool agent_connected = true;
        cdpr_servo_status_t servo;
        cdpr_servo_init(&servo);
        bool teardown_called = false;
        bool safe_stop_engaged = false;

        if (st == STATE_MOTION_ENABLED) {
            servo.is_hardware_verified = true;
            servo.torque_permitted = true;
            servo.torque_enabled = true;
            servo.current_rpms[0] = 500.0f;
        }

        simulate_agent_disconnect(&st, &agent_connected, &servo, &teardown_called, &safe_stop_engaged, false);

        TEST_ASSERT(!agent_connected, "Agent flag cleared on disconnect");
        TEST_ASSERT(teardown_called, "Entity teardown invoked");

        if (states_to_test[i] == STATE_MOTION_ENABLED) {
            TEST_ASSERT(safe_stop_engaged, "MOTION_ENABLED: Safe stop engaged BEFORE entity teardown");
            TEST_ASSERT(!servo.torque_enabled, "MOTION_ENABLED: Torque immediately disabled");
            TEST_ASSERT(servo.current_rpms[0] == 0.0f, "MOTION_ENABLED: Commanded velocity zeroed");
            TEST_ASSERT(st == STATE_WAITING_FOR_AGENT, "MOTION_ENABLED transitioned safely to WAITING_FOR_AGENT");
        } else if (states_to_test[i] == STATE_FAULT) {
            TEST_ASSERT(st == STATE_FAULT, "FAULT remains FAULT after agent loss (not cleared to WAITING_FOR_AGENT)");
        } else if (states_to_test[i] == STATE_BOOT) {
            TEST_ASSERT(st == STATE_BOOT, "Boot state preserved");
        } else if (states_to_test[i] == STATE_INITIALIZING) {
            TEST_ASSERT(st == STATE_WAITING_FOR_AGENT, "INITIALIZING transitions to WAITING_FOR_AGENT");
        } else {
            TEST_ASSERT(st == STATE_WAITING_FOR_AGENT, "State transitioned cleanly to WAITING_FOR_AGENT");
        }
    }

    /* Part 2: Unclean teardown path (injected finalization failure) -> Must land in STATE_FAULT */
    printf("\n--- Test Agent Loss with Unresolved Entities Forces STATE_FAULT ---\n");
    for (size_t i = 0; i < sizeof(states_to_test)/sizeof(states_to_test[0]); i++) {
        cdpr_firmware_state_t st = states_to_test[i];
        bool agent_connected = true;
        cdpr_servo_status_t servo;
        cdpr_servo_init(&servo);
        bool teardown_called = false;
        bool safe_stop_engaged = false;

        simulate_agent_disconnect(&st, &agent_connected, &servo, &teardown_called, &safe_stop_engaged, true);

        TEST_ASSERT(teardown_called, "Entity teardown invoked on disconnect");
        TEST_ASSERT(st == STATE_FAULT, "Unclean teardown transitions to STATE_FAULT (Fail-closed)");
        TEST_ASSERT(!servo.torque_enabled, "Torque remains disabled in STATE_FAULT");
    }
}

void test_reconnection_without_auto_arming(void) {
    printf("\n--- Test Reconnection Lifecycle (Never Auto-Arms) ---\n");

    cdpr_firmware_state_t state = STATE_WAITING_FOR_AGENT;
    bool agent_connected = false;

    /* 1. Agent discovered */
    TEST_ASSERT(cdpr_is_valid_transition(state, STATE_CONNECTED), "WAITING_FOR_AGENT -> CONNECTED valid");
    state = STATE_CONNECTED;
    agent_connected = true;
    TEST_ASSERT(agent_connected, "Agent is connected");

    /* 2. Entities created -> DRIVE_STATUS_CHECK */
    TEST_ASSERT(cdpr_is_valid_transition(state, STATE_DRIVE_STATUS_CHECK), "CONNECTED -> DRIVE_STATUS_CHECK valid");
    state = STATE_DRIVE_STATUS_CHECK;

    /* 3. Drives checked -> READY (Disarmed) */
    TEST_ASSERT(cdpr_is_valid_transition(state, STATE_READY), "DRIVE_STATUS_CHECK -> READY valid");
    state = STATE_READY;

    /* 4. VERIFY: Firmware is in READY, NOT in MOTION_ENABLED */
    TEST_ASSERT(state == STATE_READY, "Firmware landed in READY");
    TEST_ASSERT(state != STATE_MOTION_ENABLED, "Firmware did NOT auto-arm on reconnection");

    /* 5. Direct jump to MOTION_ENABLED without operator command is illegal */
    TEST_ASSERT(!cdpr_is_valid_transition(STATE_CONNECTED, STATE_MOTION_ENABLED),
                "Direct CONNECTED -> MOTION_ENABLED jump is strictly forbidden");
}

void test_agent_disconnect_from_executor_callback(void) {
    printf("\n--- Test Agent Disconnect Triggered Inside Executor Callback ---\n");

    cdpr_firmware_state_t state = STATE_MOTION_ENABLED;
    bool agent_connected = true;
    cdpr_servo_status_t servo;
    cdpr_servo_init(&servo);
    servo.is_hardware_verified = true;
    servo.torque_permitted = true;
    servo.torque_enabled = true;
    servo.current_rpms[0] = 300.0f;

    bool teardown_called = false;
    bool safe_stop_engaged = false;
    bool disconnect_pending = false;

    /* Simulate agent loss detected while executing a command callback inside executor spin */
    bool is_in_callback = true;

    /* 1. Callback engages disconnect */
    agent_connected = false;
    if (state == STATE_MOTION_ENABLED) {
        cdpr_servo_emergency_safe_stop(&servo);
        safe_stop_engaged = true;
        state = STATE_SAFE_STOP;
    }

    if (is_in_callback) {
        /* Defer teardown to avoid self-deadlock */
        disconnect_pending = true;
    } else {
        teardown_called = true;
    }

    TEST_ASSERT(!agent_connected, "Agent flag cleared immediately");
    TEST_ASSERT(safe_stop_engaged, "Emergency safe stop engaged immediately (torque disabled)");
    TEST_ASSERT(!servo.torque_enabled, "Torque is software-disabled");
    TEST_ASSERT(disconnect_pending, "Teardown is deferred until spin_some returns (no self-deadlock)");
    TEST_ASSERT(!teardown_called, "Teardown NOT called reentrantly during callback");

    /* 2. Callback returns, spin completes, and deferred teardown executes */
    is_in_callback = false;
    if (disconnect_pending) {
        disconnect_pending = false;
        teardown_called = true;
        if (cdpr_is_valid_transition(state, STATE_WAITING_FOR_AGENT)) {
            state = STATE_WAITING_FOR_AGENT;
        }
    }

    TEST_ASSERT(teardown_called, "Deferred teardown executed after spin completion");
    TEST_ASSERT(state == STATE_WAITING_FOR_AGENT, "State safely reached WAITING_FOR_AGENT");
}

int main(void) {
    printf("===============================================================\n");
    printf("   CDPR Agent Lifecycle & Teardown Unit Tests (HOST-ONLY)      \n");
    printf("   NOTE: Validates software logic only; NOT hardware safety    \n");
    printf("===============================================================\n");

    test_entity_creation_failure_paths();
    test_simulated_teardown_failures();
    test_executor_spinning_guard();
    test_agent_loss_across_fsm_states();
    test_agent_disconnect_from_executor_callback();
    test_reconnection_without_auto_arming();

    printf("\n===============================================================\n");
    printf(" Results: %d / %d tests passed\n", g_tests_passed, g_tests_run);
    printf("===============================================================\n");

    return (g_tests_passed == g_tests_run) ? 0 : 1;
}
