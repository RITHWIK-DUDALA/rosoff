#include "esp32_serial_transport.h"
#include <uxr/client/transport.h>

#include <driver/uart.h>
#include <driver/gpio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#ifndef CONFIG_MICROROS_UART_TXD
#define CONFIG_MICROROS_UART_TXD 17
#endif

#ifndef CONFIG_MICROROS_UART_RXD
#define CONFIG_MICROROS_UART_RXD 16
#endif

#ifndef CONFIG_MICROROS_UART_RTS
#define CONFIG_MICROROS_UART_RTS -1
#endif

#ifndef CONFIG_MICROROS_UART_CTS
#define CONFIG_MICROROS_UART_CTS -1
#endif

#define UART_BUFFER_SIZE (1024)

bool esp32_serial_open(struct uxrCustomTransport * transport){
    if (transport == NULL || transport->args == NULL) {
        return false;
    }
    size_t * uart_port = (size_t*) transport->args;

    uart_config_t uart_config = {
        .baud_rate = 115200,
        .data_bits = UART_DATA_8_BITS,
        .parity    = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_DEFAULT,
    };

    if (uart_is_driver_installed((uart_port_t)*uart_port)) {
        uart_driver_delete((uart_port_t)*uart_port);
    }

    if (uart_param_config((uart_port_t)*uart_port, &uart_config) != ESP_OK) {
        return false;
    }
    if (uart_set_pin((uart_port_t)*uart_port, CONFIG_MICROROS_UART_TXD, CONFIG_MICROROS_UART_RXD,
                     CONFIG_MICROROS_UART_RTS, CONFIG_MICROROS_UART_CTS) != ESP_OK) {
        return false;
    }
    if (uart_driver_install((uart_port_t)*uart_port, UART_BUFFER_SIZE * 2, UART_BUFFER_SIZE * 2, 0, NULL, 0) != ESP_OK) {
        return false;
    }

    return true;
}

bool esp32_serial_close(struct uxrCustomTransport * transport){
    if (transport == NULL || transport->args == NULL) {
        return false;
    }
    size_t * uart_port = (size_t*) transport->args;

    if (uart_is_driver_installed((uart_port_t)*uart_port)) {
        return (uart_driver_delete((uart_port_t)*uart_port) == ESP_OK);
    }
    return true;
}

size_t esp32_serial_write(struct uxrCustomTransport* transport, const uint8_t * buf, size_t len, uint8_t * err){
    if (transport == NULL || transport->args == NULL || buf == NULL) {
        if (err != NULL) *err = 1;
        return 0;
    }
    size_t * uart_port = (size_t*) transport->args;
    const int txBytes = uart_write_bytes((uart_port_t)*uart_port, (const char*) buf, len);
    if (txBytes < 0) {
        if (err != NULL) *err = 1;
        return 0;
    }
    if (err != NULL) *err = 0;
    return (size_t)txBytes;
}

size_t esp32_serial_read(struct uxrCustomTransport* transport, uint8_t* buf, size_t len, int timeout, uint8_t* err){
    if (transport == NULL || transport->args == NULL || buf == NULL) {
        if (err != NULL) *err = 1;
        return 0;
    }
    size_t * uart_port = (size_t*) transport->args;
    TickType_t ticks = 0;
    if (timeout > 0) {
        ticks = pdMS_TO_TICKS(timeout);
        if (ticks == 0) {
            ticks = 1; /* Wait at least 1 tick on positive timeout */
        }
    }
    const int rxBytes = uart_read_bytes((uart_port_t)*uart_port, buf, len, ticks);
    if (rxBytes < 0) {
        if (err != NULL) *err = 1;
        return 0;
    }
    if (err != NULL) *err = 0;
    return (size_t)rxBytes;
}
