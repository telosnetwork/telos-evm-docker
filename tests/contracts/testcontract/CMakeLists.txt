cmake_minimum_required(VERSION 3.5)
project(test_contract VERSION 0.1.0)
find_package(cdt)
include(CDTWasmToolchain)

add_contract(testcontract testcontract testcontract.cpp)

file(GLOB custom_includes ${CUSTOM_INCLUDES_DIR}/*)
target_include_directories(testcontract PUBLIC ${custom_includes})
