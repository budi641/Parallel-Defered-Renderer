cmake_minimum_required(VERSION 3.10)
project(Parallel-Deferred-Renderer LANGUAGES C CXX)

# Require C++11 or higher
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Enable OpenMP
find_package(OpenMP)
if(OpenMP_CXX_FOUND)
    message(STATUS "OpenMP found: ${OpenMP_CXX_VERSION}")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${OpenMP_CXX_FLAGS}")
else()
    message(WARNING "OpenMP not found! Proceeding without it.")
endif()

# GLFW
option(GLFW_BUILD_DOCS OFF)
option(GLFW_BUILD_EXAMPLES OFF)
option(GLFW_BUILD_TESTS OFF)
add_subdirectory(api/glfw)

# ASSIMP
option(ASSIMP_BUILD_ASSIMP_TOOLS OFF)
option(ASSIMP_BUILD_SAMPLES OFF)
option(ASSIMP_BUILD_TESTS OFF)
add_subdirectory(api/assimp)

# Compiler warnings
if(MSVC)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} /W4")
else()
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra -Wpedantic")
    if(NOT WIN32)
        set(GLAD_LIBRARIES dl)
    endif()
endif()

# Include directories
include_directories(
    src/camera/
    src/lighting/
    src/mesh/
    src/renderer/
    src/resources/
    api/assimp/include/
    api/glad/include/
    api/glfw/include/
    api/glm/
    api/stb/
    api/imgui/
)

# Source and header files
file(GLOB API_SOURCES
    api/glad/src/glad.c
    api/imgui/*.cpp
)

file(GLOB PROJECT_HEADERS
    src/camera/*.h
    src/lighting/*.h
    src/mesh/*.h
    src/renderer/*.h
    src/resources/*.h
)

file(GLOB PROJECT_SOURCES
    src/camera/*.cpp
    src/lighting/*.cpp
    src/mesh/*.cpp
    src/renderer/parallel-deferred-renderer_omp.cpp
    src/resources/*.cpp
)

file(GLOB PROJECT_SHADERS
    resources/shaders/**/*.glsl
    resources/shaders/**/*.frag
    resources/shaders/**/*.vert
)

# Grouping for IDEs
source_group("Headers" FILES ${PROJECT_HEADERS})
source_group("Shaders" FILES ${PROJECT_SHADERS})
source_group("Sources" FILES ${PROJECT_SOURCES})
source_group("API" FILES ${API_SOURCES})

# Executable
add_definitions(-DGLFW_INCLUDE_NONE -DPROJECT_SOURCE_DIR=\"${PROJECT_SOURCE_DIR}\")
add_executable(${PROJECT_NAME}
    ${PROJECT_SOURCES}
    ${PROJECT_HEADERS}
    ${PROJECT_SHADERS}
    ${API_SOURCES}
)

# Link libraries
target_link_libraries(${PROJECT_NAME} PRIVATE assimp glfw ${GLFW_LIBRARIES} ${GLAD_LIBRARIES})

# Add OpenMP linking if found
if(OpenMP_CXX_FOUND)
    target_link_libraries(${PROJECT_NAME} PRIVATE OpenMP::OpenMP_CXX)
endif()

# Output binary directory
set_target_properties(${PROJECT_NAME} PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}
)
