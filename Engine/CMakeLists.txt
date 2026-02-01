cmake_minimum_required(VERSION 3.15)
project(QuantEngine VERSION 1.0.0 LANGUAGES CXX)

# -----------------------------------------------------------------------------
#  Configuration
# -----------------------------------------------------------------------------
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Performance Flags
if(MSVC)
    add_compile_options(/O2 /arch:AVX2 /W4 /permissive-)
else()
    add_compile_options(-O3 -march=native -Wall -Wextra -Wpedantic)
endif()

# Output directories
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)

# -----------------------------------------------------------------------------
# QuantEngine Library (Core Logic)
# -----------------------------------------------------------------------------
include_directories(include)

# Gather sources (GLOB is okay for rapid dev, but list is better for stability)
file(GLOB_RECURSE ENGINE_SOURCES "src/*.cpp")

# Exclude main.cpp from the library if it exists in src/
list(FILTER ENGINE_SOURCES EXCLUDE REGEX ".*src/main\\.cpp$")

add_library(QuantEngineLib STATIC ${ENGINE_SOURCES})

# -----------------------------------------------------------------------------
#  QuantEngine Executable (Runner)
# -----------------------------------------------------------------------------
add_executable(QuantEngineApp src/main.cpp)
target_link_libraries(QuantEngineApp PRIVATE QuantEngineLib)


