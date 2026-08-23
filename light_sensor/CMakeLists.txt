cmake_minimum_required(VERSION 3.16)
project(light_sensor CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

option(PLATFORM_LINUX  "Linux/OpenWrt" OFF)
option(PLATFORM_TEST   "Test mode" OFF)

set(PLATFORM_COUNT 0)
if(PLATFORM_LINUX)
    math(EXPR PLATFORM_COUNT "${PLATFORM_COUNT} + 1")
endif()
if(PLATFORM_TEST)
    math(EXPR PLATFORM_COUNT "${PLATFORM_COUNT} + 1")
endif()

if(${PLATFORM_COUNT} GREATER 1)
    message(FATAL_ERROR "Choose exactly one platform: PLATFORM_LINUX / PLATFORM_TEST")
endif()
if(${PLATFORM_COUNT} EQUAL 0)
    message(FATAL_ERROR "Specify one platform, e.g. -DPLATFORM_LINUX=ON or -DPLATFORM_TEST=ON")
endif()

# Привязываем опции к макросам для config.hpp
if(PLATFORM_LINUX)
    add_compile_definitions(PLATFORM_LINUX=1)
    message(STATUS "Сборка: Linux/Orange Pi (UDP POSIX)")
elseif(PLATFORM_TEST)
    add_compile_definitions(PLATFORM_TEST=1)
    message(STATUS "Сборка: Тест (NullTransport)")
endif()

set(BASE_SOURCES
    src/main.cpp
    src/app_core.cpp 
    src/sensors/stub.cpp
)
add_executable(${PROJECT_NAME} ${BASE_SOURCES})

target_include_directories(${PROJECT_NAME} PRIVATE ${CMAKE_SOURCE_DIR}/include)

# Добавляем транспорт в зависимости от платформы
if(PLATFORM_LINUX)
    target_sources(${PROJECT_NAME} PRIVATE src/transports/udp_posix.cpp)
elseif(PLATFORM_TEST)
    target_sources(${PROJECT_NAME} PRIVATE src/transports/null.cpp)
endif()

if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    target_compile_options(${PROJECT_NAME} PRIVATE -O2 -Wall)
endif()
