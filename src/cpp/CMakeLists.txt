cmake_minimum_required(VERSION 3.24)

project(PacketParser LANGUAGES CXX)

enable_testing() # Why?

add_subdirectory(src)

include(FetchContent)

# GoogleTest v1.16.0, released 7 Feb 2025
FetchContent_Declare(
    googletest
    URL https://github.com/google/googletest/archive/6910c9d9165801d8827d628cb72eb7ea9dd538c5.zip
)
FetchContent_MakeAvailable(googletest)

# Moves out of this directory to tests/cpp/CmakeLists.txt
add_subdirectory(
    ${CMAKE_CURRENT_SOURCE_DIR}/../../tests/cpp
    ${CMAKE_BINARY_DIR}/tests
)
