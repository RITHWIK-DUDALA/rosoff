idf_component_register(
    SRCS
        "main.c"
        "esp32_serial_transport.c"
        "cdpr_command_validator.c"
        "cdpr_feedback_interface.c"
    INCLUDE_DIRS "."
    REQUIRES
        freertos
        esp_timer
        driver
        micro_ros_espidf_component
)
