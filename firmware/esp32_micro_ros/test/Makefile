CC = gcc
CFLAGS = -Wall -Wextra -Werror -I../main -std=c11
PTHREAD_FLAGS = -pthread

TESTS = test_state_machine \
        test_command_validator \
        test_servo_interface \
        test_feedback_interface \
        test_watchdog_and_recovery \
        test_agent_lifecycle \
        test_concurrency

all: $(TESTS)

test_state_machine: test_state_machine.c ../main/app_state.h
	$(CC) $(CFLAGS) -o $@ test_state_machine.c

test_command_validator: test_command_validator.c ../main/cdpr_command_validator.c ../main/cdpr_command_validator.h ../main/app_state.h
	$(CC) $(CFLAGS) -o $@ test_command_validator.c ../main/cdpr_command_validator.c -lm

test_servo_interface: test_servo_interface.c ../main/servo_driver_interface.h
	$(CC) $(CFLAGS) -o $@ test_servo_interface.c

test_feedback_interface: test_feedback_interface.c ../main/cdpr_feedback_interface.c ../main/cdpr_feedback_interface.h ../main/servo_driver_interface.h
	$(CC) $(CFLAGS) -o $@ test_feedback_interface.c ../main/cdpr_feedback_interface.c -lm

test_watchdog_and_recovery: test_watchdog_and_recovery.c ../main/app_state.h ../main/servo_driver_interface.h
	$(CC) $(CFLAGS) -o $@ test_watchdog_and_recovery.c

test_agent_lifecycle: test_agent_lifecycle.c ../main/app_state.h ../main/servo_driver_interface.h
	$(CC) $(CFLAGS) -o $@ test_agent_lifecycle.c

test_concurrency: test_concurrency.c ../main/app_state.h ../main/servo_driver_interface.h ../main/cdpr_command_validator.c ../main/cdpr_command_validator.h
	$(CC) $(CFLAGS) $(PTHREAD_FLAGS) -o $@ test_concurrency.c ../main/cdpr_command_validator.c -lm

run: all
	@echo "=========================================================="
	@echo "  RUNNING FULL CDPR FIRMWARE SAFETY & LIFECYCLE TEST SUITE "
	@echo "=========================================================="
	@./test_state_machine
	@./test_command_validator
	@./test_servo_interface
	@./test_feedback_interface
	@./test_watchdog_and_recovery
	@./test_agent_lifecycle
	@./test_concurrency
	@echo "=========================================================="
	@echo "  ALL 7 UNIT TEST SUITES PASSED SUCCESSFULLY!             "
	@echo "=========================================================="

clean:
	rm -f $(TESTS)
