cmake_minimum_required(VERSION 3.15)
project(QuantEngine)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find Python for pybind11
find_package(pybind11 REQUIRED)

# Include directories
include_directories(include)

# Source files
set(SOURCES
    src/features.cpp
    src/backtest.cpp
    src/data_handler.cpp
)

# Header files
set(HEADERS
    include/features.hpp
    include/backtest.hpp
    include/data_handler.hpp
)

# Python module
pybind11_add_module(quant_engine python_bindings/pybind_module.cpp ${SOURCES})

# Compiler flags
target_compile_options(quant_engine PRIVATE -O3 -march=native)

# Example: If using Eigen (uncomment if needed)
# find_package(Eigen3 REQUIRED)
# target_link_libraries(quant_engine PRIVATE Eigen3::Eigen)
