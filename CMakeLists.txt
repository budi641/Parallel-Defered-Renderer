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

# Enable MPI
# On Windows, try to find MS-MPI (Microsoft MPI)
set(MPI_CXX_FOUND FALSE)
if(WIN32)
    message(STATUS "Searching for MS-MPI...")
    
    # Check environment variables first
    set(MSMPI_INC_PATH "$ENV{MSMPI_INC}")
    set(MSMPI_LIB_PATH "$ENV{MSMPI_LIB}")
    
    # If not in env vars, check common installation paths
    if(NOT MSMPI_INC_PATH OR NOT EXISTS "${MSMPI_INC_PATH}/mpi.h")
        set(COMMON_PATHS
            "C:/Program Files (x86)/Microsoft SDKs/MPI"
            "C:/Program Files/Microsoft SDKs/MPI"
            "C:/Program Files (x86)/Microsoft MPI"
            "C:/Program Files/Microsoft MPI"
        )
        foreach(PATH ${COMMON_PATHS})
            if(EXISTS "${PATH}/Include/mpi.h")
                set(MSMPI_INC_PATH "${PATH}/Include")
                message(STATUS "Found MS-MPI include in: ${MSMPI_INC_PATH}")
                break()
            elseif(EXISTS "${PATH}/Inc/mpi.h")
                set(MSMPI_INC_PATH "${PATH}/Inc")
                message(STATUS "Found MS-MPI include in: ${MSMPI_INC_PATH}")
                break()
            endif()
        endforeach()
    endif()
    
    if(NOT MSMPI_LIB_PATH OR NOT EXISTS "${MSMPI_LIB_PATH}/x64/msmpi.lib")
        # Try to find library path
        set(COMMON_LIB_PATHS
            "C:/Program Files (x86)/Microsoft SDKs/MPI/Lib/x64"
            "C:/Program Files/Microsoft SDKs/MPI/Lib/x64"
            "C:/Program Files (x86)/Microsoft MPI/Lib/x64"
            "C:/Program Files/Microsoft MPI/Lib/x64"
        )
        foreach(PATH ${COMMON_LIB_PATHS})
            if(EXISTS "${PATH}/msmpi.lib")
                set(MSMPI_LIB_PATH "${PATH}")
                message(STATUS "Found MS-MPI library in: ${MSMPI_LIB_PATH}")
                break()
            endif()
        endforeach()
    endif()
    
    # Verify we found both include and library
    if(MSMPI_INC_PATH AND EXISTS "${MSMPI_INC_PATH}/mpi.h")
        include_directories("${MSMPI_INC_PATH}")
        set(MPI_CXX_FOUND TRUE)
        
        # Find MS-MPI libraries
        if(MSMPI_LIB_PATH AND EXISTS "${MSMPI_LIB_PATH}/msmpi.lib")
            set(MPI_CXX_LIBRARIES "${MSMPI_LIB_PATH}/msmpi.lib")
            message(STATUS "Using MS-MPI library: ${MPI_CXX_LIBRARIES}")
        elseif(MSMPI_LIB_PATH AND EXISTS "${MSMPI_LIB_PATH}/x64/msmpi.lib")
            set(MPI_CXX_LIBRARIES "${MSMPI_LIB_PATH}/x64/msmpi.lib")
            message(STATUS "Using MS-MPI library: ${MPI_CXX_LIBRARIES}")
        else()
            message(WARNING "MS-MPI include found but library not found. Checking common locations...")
            # Try to find library relative to include path
            get_filename_component(MSMPI_BASE "${MSMPI_INC_PATH}" DIRECTORY)
            if(EXISTS "${MSMPI_BASE}/Lib/x64/msmpi.lib")
                set(MPI_CXX_LIBRARIES "${MSMPI_BASE}/Lib/x64/msmpi.lib")
                message(STATUS "Found MS-MPI library: ${MPI_CXX_LIBRARIES}")
            elseif(EXISTS "${MSMPI_BASE}/Lib/msmpi.lib")
                set(MPI_CXX_LIBRARIES "${MSMPI_BASE}/Lib/msmpi.lib")
                message(STATUS "Found MS-MPI library: ${MPI_CXX_LIBRARIES}")
            else()
                set(MPI_CXX_FOUND FALSE)
                message(WARNING "MS-MPI library not found. MPI will be disabled.")
            endif()
        endif()
    else()
        message(STATUS "MS-MPI not found in standard locations. Trying standard find_package...")
        find_package(MPI)
    endif()
else()
    # On Linux/Mac, use standard MPI find
    find_package(MPI)
endif()

if(MPI_CXX_FOUND)
    message(STATUS "MPI found and enabled!")
    if(NOT WIN32)
        include_directories(${MPI_CXX_INCLUDE_PATH})
    endif()
    add_definitions(-DHAVE_MPI)
else()
    message(STATUS "MPI not found! MPI features will be disabled (code will compile without MPI).")
    message(STATUS "")
    message(STATUS "To enable MPI on Windows:")
    message(STATUS "  1. Install MS-MPI SDK from: https://www.microsoft.com/en-us/download/details.aspx?id=57467")
    message(STATUS "  2. Set environment variables:")
    message(STATUS "     MSMPI_INC=C:/Program Files (x86)/Microsoft SDKs/MPI/Include")
    message(STATUS "     MSMPI_LIB=C:/Program Files (x86)/Microsoft SDKs/MPI/Lib/x64")
    message(STATUS "  3. Or pass to CMake:")
    message(STATUS "     cmake -DMSMPI_INC=\"C:/Program Files (x86)/Microsoft SDKs/MPI/Include\" -DMSMPI_LIB=\"C:/Program Files (x86)/Microsoft SDKs/MPI/Lib/x64\"")
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
    src/renderer/mpi_domain_decomposition.cpp
    src/renderer/mpi_performance.cpp
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

# Add MPI linking if found
if(MPI_CXX_FOUND)
    target_link_libraries(${PROJECT_NAME} PRIVATE ${MPI_CXX_LIBRARIES})
endif()

# Output binary directory
set_target_properties(${PROJECT_NAME} PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}
)
