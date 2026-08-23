#include <cstdint>

#if defined(PLATFORM_ESP32)
    #include "sensors/bh1750.h"
#else
    #include "sensors/stub.h"
#endif

#include "config.hpp"
#include "platform_delay.hpp"
#include "app_core.h"

template <typename T>
void run_application(T& transport, LightSensor& sensor) {
    uint8_t packet[3];

    while (true) {
        const int lux = sensor.readLux();
        uint16_t lux16 = 0;
        if (lux > 0) {
            lux16 = (lux > 65535) ? 65535 : static_cast<uint16_t>(lux);
        }

        // Заполняем пакет строго по формату light_control: [ID][level]
        packet[0] = DEVICE_ID;
        packet[1] = static_cast<uint8_t>(lux16 >> 8);
        packet[2] = static_cast<uint8_t>(lux16 & 0xFF);

        transport.send(packet, sizeof(packet));

        platform_delay_ms(SAMPLE_PERIOD_MS);
    }
}

// ============================================================
// ЯВНАЯ ИНСТАНЦИАЦИЯ (ТОЛЬКО ЗДЕСЬ, В КОНЦЕ .CPP)
// ============================================================
#if defined(PLATFORM_LINUX) || defined(TRANSPORT_HAS_IP_AND_PORT)
    #include "transports/udp_posix.h"

    template void run_application<TransportWrapper<UdpPosixTransport>>(
        TransportWrapper<UdpPosixTransport>&, LightSensor&);

#elif defined(PLATFORM_ESP32)
    #include "transports/wifi_esp32.h"   

    template void run_application<TransportWrapper<WifiEsp32Transport >>(
        TransportWrapper<WifiEsp32Transport >&, LightSensor&);

#elif defined(PLATFORM_TEST)
    #include "transports/null.h"   

    template void run_application<TransportWrapper<NullTransport >>(
        TransportWrapper<NullTransport >&, LightSensor&);

#else
    #error "Не определена целевая платформа: PLATFORM_LINUX или PLATFORM_ESP32"

#endif
