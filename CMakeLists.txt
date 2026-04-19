cmake_minimum_required(VERSION 3.26)
project(UnifiedQuantum)
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/UniqcCpp/src
                    ${CMAKE_CURRENT_SOURCE_DIR}/UniqcCpp/Thirdparty
                    ${CMAKE_CURRENT_SOURCE_DIR}/UniqcCpp/Thirdparty/pybind11
                    ${CMAKE_CURRENT_SOURCE_DIR}/UniqcCpp/Thirdparty/fmt/include
                    )

set(LIBRARY_OUTPUT_PATH ${CMAKE_CURRENT_BINARY_DIR}/lib)
set(EXECUTABLE_OUTPUT_PATH ${CMAKE_CURRENT_BINARY_DIR}/bin)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY_DEBUG ${CMAKE_CURRENT_BINARY_DIR}/bin)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY_RELEASE ${CMAKE_CURRENT_BINARY_DIR}/bin)
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY_DEBUG ${CMAKE_CURRENT_BINARY_DIR}/lib)
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY_RELEASE ${CMAKE_CURRENT_BINARY_DIR}/lib)

set(CMAKE_CXX_STANDARD 17)

if (UNIX)
    add_definitions("-fPIC")
endif()

# Python detection is handled by pybind11 in Thirdparty/pybind11
# pybind11_add_module will automatically find the correct Python version

add_subdirectory(UniqcCpp)
