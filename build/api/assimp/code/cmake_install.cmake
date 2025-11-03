# Install script for directory: /home/joe/Parallel-Defered-Renderer/api/assimp/code

# Set the install prefix
if(NOT DEFINED CMAKE_INSTALL_PREFIX)
  set(CMAKE_INSTALL_PREFIX "/usr/local")
endif()
string(REGEX REPLACE "/$" "" CMAKE_INSTALL_PREFIX "${CMAKE_INSTALL_PREFIX}")

# Set the install configuration name.
if(NOT DEFINED CMAKE_INSTALL_CONFIG_NAME)
  if(BUILD_TYPE)
    string(REGEX REPLACE "^[^A-Za-z0-9_]+" ""
           CMAKE_INSTALL_CONFIG_NAME "${BUILD_TYPE}")
  else()
    set(CMAKE_INSTALL_CONFIG_NAME "")
  endif()
  message(STATUS "Install configuration: \"${CMAKE_INSTALL_CONFIG_NAME}\"")
endif()

# Set the component getting installed.
if(NOT CMAKE_INSTALL_COMPONENT)
  if(COMPONENT)
    message(STATUS "Install component: \"${COMPONENT}\"")
    set(CMAKE_INSTALL_COMPONENT "${COMPONENT}")
  else()
    set(CMAKE_INSTALL_COMPONENT)
  endif()
endif()

# Install shared libraries without execute permission?
if(NOT DEFINED CMAKE_INSTALL_SO_NO_EXE)
  set(CMAKE_INSTALL_SO_NO_EXE "1")
endif()

# Is this installation the result of a crosscompile?
if(NOT DEFINED CMAKE_CROSSCOMPILING)
  set(CMAKE_CROSSCOMPILING "FALSE")
endif()

# Set default install directory permissions.
if(NOT DEFINED CMAKE_OBJDUMP)
  set(CMAKE_OBJDUMP "/usr/bin/objdump")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib" TYPE STATIC_LIBRARY FILES "/home/joe/Parallel-Defered-Renderer/build/api/assimp/code/libassimp.a")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "assimp-dev" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/include/assimp" TYPE FILE FILES
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/anim.h"
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/ai_assert.h"
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/camera.h"
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/color4.h"
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/color4.inl"
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/config.h"
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/defs.h"
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/cfileio.h"
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/light.h"
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/material.h"
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/material.inl"
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/matrix3x3.h"
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/matrix3x3.inl"
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/matrix4x4.h"
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/matrix4x4.inl"
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/mesh.h"
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/postprocess.h"
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/quaternion.h"
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/quaternion.inl"
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/scene.h"
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/metadata.h"
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/texture.h"
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/types.h"
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/vector2.h"
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/vector2.inl"
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/vector3.h"
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/vector3.inl"
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/version.h"
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/cimport.h"
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/importerdesc.h"
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/Importer.hpp"
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/DefaultLogger.hpp"
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/ProgressHandler.hpp"
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/IOStream.hpp"
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/IOSystem.hpp"
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/Logger.hpp"
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/LogStream.hpp"
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/NullLogger.hpp"
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/cexport.h"
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/Exporter.hpp"
    )
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "assimp-dev" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/include/assimp/Compiler" TYPE FILE FILES
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/Compiler/pushpack1.h"
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/Compiler/poppack1.h"
    "/home/joe/Parallel-Defered-Renderer/api/assimp/code/../include/assimp/Compiler/pstdint.h"
    )
endif()

