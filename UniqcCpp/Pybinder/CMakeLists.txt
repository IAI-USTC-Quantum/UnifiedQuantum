cmake_minimum_required(VERSION 3.22)
project(uniqc_cpp)

file(GLOB_RECURSE UniqcCppWrapper_SRC_CPP *.cpp)

pybind11_add_module(${PROJECT_NAME} ${UniqcCppWrapper_SRC_CPP})

target_link_libraries(${PROJECT_NAME} PRIVATE UniqcCppCore fmt)
