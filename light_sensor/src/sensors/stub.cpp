#include <iostream>
#include "config.hpp"
#include "sensors/stub.h"

Stub::Stub(SensorScenario scenario)
    : _scenario(scenario) {}

bool Stub::init(uint8_t /*address*/) {
    return true;
}

int Stub::readLux() {
    int retVal {0};

    switch (_scenario) {
        case SensorScenario::Morning:  
            retVal = 450;
        break;

        case SensorScenario::Evening:  
            retVal = 220;
        break;

        case SensorScenario::Night: 
            retVal = 50;
        break;

        default:
            std::cout << "[STUB SENSOR, readLux]  Urecognized _scenario value!" << '\n';
            retVal = 200;
    }

    std::cout << "[STUB SENSOR] device_id=" << static_cast<int>(DEVICE_ID)
                << " lux=" << retVal << '\n';
    
    return retVal;
}
