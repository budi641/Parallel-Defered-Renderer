# Parallel-Deferred-Renderer Build System

This directory contains several build scripts for the Parallel-Deferred-Renderer project.

## Available Build Scripts

### 1. `build_and_run.bat` (Recommended)
The main build script with full functionality.

**Usage:**
```bash
build_and_run.bat [CONFIG] [OPTIONS]
```

**Configurations:**
- `Debug` - Debug build with symbols and debugging information
- `Release` - Optimized release build
- `Shipping` - Same as Release (alias)

**Options:**
- `--clean` - Clean previous builds before building
- `--run` - Run the application after successful build
- `--verbose` - Show detailed build output
- `--help` - Show help message

**Examples:**
```bash
# Debug build
build_and_run.bat Debug

# Release build with clean and run
build_and_run.bat Release --clean --run

# Debug build with verbose output
build_and_run.bat Debug --verbose

# Show help
build_and_run.bat --help
```

### 2. `build_and_run_advanced.bat`
Enhanced version with additional features and better error handling.

### 3. `quick_build.bat`
Simple script for quick Debug builds and immediate execution.

## Prerequisites

Before building, ensure you have:

1. **CMake** (3.0 or higher)
2. **C++ Compiler** (Visual Studio 2019+ or MinGW)
3. **Required Libraries:**
   - OpenGL
   - GLFW
   - GLM
   - Assimp
   - STB
   - ImGui

## Project Structure

```
Parallel-Deferred-Renderer/
├── build_Debug/          # Debug build output
├── build_Release/        # Release build output
├── src/                  # Source code
├── resources/            # Assets (models, textures, shaders)
├── api/                  # Third-party libraries
├── CMakeLists.txt        # Main CMake configuration
└── build_and_run.bat     # Main build script
```

## Build Process

1. **Configuration**: CMake generates build files
2. **Compilation**: Source files are compiled
3. **Linking**: Object files are linked into executable
4. **Resource Copy**: Assets are copied to build directory
5. **Execution**: Application runs (if requested)

## Troubleshooting

### Common Issues

**CMake not found:**
- Install CMake and add it to your system PATH
- Or use Visual Studio's built-in CMake support

**Compiler not found:**
- Install Visual Studio Build Tools
- Or install MinGW-w64
- Ensure compiler is in your PATH

**Build fails:**
- Check error messages in the console
- Verify all dependencies are installed
- Try cleaning the build directory (`--clean`)

**Executable not found:**
- Check if build completed successfully
- Look for .exe files in build directories
- Verify CMake configuration

### Build Directories

- `build_Debug/` - Contains Debug build artifacts
- `build_Release/` - Contains Release build artifacts
- Each directory is self-contained and can be deleted safely

## Configuration

Edit `build_config.txt` to customize build settings:
- Project name
- Default configuration
- Build options
- Compiler flags

## Development Workflow

1. **First Build:**
   ```bash
   build_and_run.bat Debug --clean --run
   ```

2. **Development:**
   ```bash
   build_and_run.bat Debug --run
   ```

3. **Release Build:**
   ```bash
   build_and_run.bat Release --clean --run
   ```

4. **Quick Testing:**
   ```bash
   quick_build.bat
   ```

## Notes

- The project uses CMake for cross-platform builds
- Debug builds include debugging symbols and are not optimized
- Release builds are optimized for performance
- Resources are automatically copied to the build directory
- The executable name matches the project name: `Parallel-Deferred-Renderer.exe`
