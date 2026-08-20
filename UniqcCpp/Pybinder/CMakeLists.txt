project(uniqc_cpp)

pybind11_add_module(${PROJECT_NAME} uniqc_cpp.cpp)

target_link_libraries(${PROJECT_NAME} PRIVATE UniqcCppCore fmt)
