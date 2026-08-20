cmake_minimum_required(VERSION 3.22)
project(UnifiedQuantum)
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/UniqcCpp/src
                    ${CMAKE_CURRENT_SOURCE_DIR}/UniqcCpp/Thirdparty
                    ${CMAKE_CURRENT_SOURCE_DIR}/UniqcCpp/Thirdparty/fmt/include
                    )

set(LIBRARY_OUTPUT_PATH ${CMAKE_CURRENT_BINARY_DIR}/lib)
set(EXECUTABLE_OUTPUT_PATH ${CMAKE_CURRENT_BINARY_DIR}/bin)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY_DEBUG ${CMAKE_CURRENT_BINARY_DIR}/bin/Debug)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY_RELEASE ${CMAKE_CURRENT_BINARY_DIR}/bin/Release)
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY_DEBUG ${CMAKE_CURRENT_BINARY_DIR}/lib/Debug)
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY_RELEASE ${CMAKE_CURRENT_BINARY_DIR}/lib/Release)

set(CMAKE_CXX_STANDARD 17)

set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# Security hardening flags for Release builds (GCC/Clang only; MSVC uses
# its own mitigations and would reject these ELF-specific linker options).
if (CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    add_compile_options($<$<CONFIG:Release>:-fstack-protector-strong>)
    add_compile_options($<$<CONFIG:Release>:-D_FORTIFY_SOURCE=2>)
    if (NOT APPLE)
        add_link_options($<$<CONFIG:Release>:-Wl,-z,relro,-z,now>)
        add_link_options($<$<CONFIG:Release>:-Wl,--strip-all>)
    endif()
endif()

set(PYBIND11_FINDPYTHON ON)
find_package(pybind11 CONFIG REQUIRED)

add_subdirectory(UniqcCpp)
