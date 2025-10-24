@echo off
setlocal enabledelayedexpansion

REM ========================================
REM Parallel-Deferred-Renderer Build Script (Advanced)
REM ========================================

REM Default configuration
set CONFIG=Debug
set PROJECT_NAME=Parallel-Deferred-Renderer
set CLEAN_BUILD=false
set RUN_AFTER_BUILD=false
set VERBOSE_BUILD=false

REM Parse command line arguments
:parse_args
if "%1"=="" goto :args_done
if "%1"=="Debug" set CONFIG=Debug
if "%1"=="Release" set CONFIG=Release
if "%1"=="Shipping" set CONFIG=Release
if "%1"=="debug" set CONFIG=Debug
if "%1"=="release" set CONFIG=Release
if "%1"=="shipping" set CONFIG=Release
if "%1"=="--clean" set CLEAN_BUILD=true
if "%1"=="--run" set RUN_AFTER_BUILD=true
if "%1"=="--verbose" set VERBOSE_BUILD=true
if "%1"=="--help" goto :show_help
shift
goto :parse_args

:args_done

REM Show help if requested
if "%1"=="--help" goto :show_help

REM Display configuration
echo.
echo ========================================
echo %PROJECT_NAME% Build System
echo ========================================
echo Configuration: %CONFIG%
echo Clean Build: %CLEAN_BUILD%
echo Run After Build: %RUN_AFTER_BUILD%
echo Verbose Build: %VERBOSE_BUILD%
echo ========================================
echo.

REM Set paths
set BUILD_DIR=build_%CONFIG%
set EXECUTABLE_NAME=%PROJECT_NAME%
set RESOURCES_DIR=resources

REM Check if we're in the right directory
if not exist "CMakeLists.txt" (
    echo ERROR: CMakeLists.txt not found!
    echo Please run this script from the project root directory.
    pause
    exit /b 1
)

REM Check for required dependencies
echo Checking dependencies...
where cmake >nul 2>&1
if errorlevel 1 (
    echo ERROR: CMake not found in PATH!
    echo Please install CMake and add it to your system PATH.
    pause
    exit /b 1
)

where gcc >nul 2>&1
if errorlevel 1 (
    where cl >nul 2>&1
    if errorlevel 1 (
        echo WARNING: No C++ compiler found in PATH!
        echo Make sure you have Visual Studio or MinGW installed.
    )
)

REM Clean build if requested
if "%CLEAN_BUILD%"=="true" (
    echo Cleaning previous builds...
    if exist "build_Debug" rmdir /s /q "build_Debug"
    if exist "build_Release" rmdir /s /q "build_Release"
    echo Clean completed.
    echo.
)

REM Create build directory
if not exist "%BUILD_DIR%" (
    echo Creating build directory: %BUILD_DIR%
    mkdir "%BUILD_DIR%"
)

cd "%BUILD_DIR%"

REM Configure CMake
echo Configuring CMake...
if "%CONFIG%"=="Debug" (
    cmake .. -DCMAKE_BUILD_TYPE=Debug -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
) else (
    cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
)

if errorlevel 1 (
    echo.
    echo ERROR: CMake configuration failed!
    echo.
    echo Common solutions:
    echo 1. Make sure all dependencies are installed
    echo 2. Check that CMake can find your compiler
    echo 3. Verify the CMakeLists.txt file is valid
    echo.
    pause
    exit /b 1
)

REM Build the project
echo.
echo Building %PROJECT_NAME%...
if "%VERBOSE_BUILD%"=="true" (
    cmake --build . --config %CONFIG% --parallel --verbose
) else (
    cmake --build . --config %CONFIG% --parallel
)

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    echo.
    echo Common solutions:
    echo 1. Check for compilation errors above
    echo 2. Ensure all source files are present
    echo 3. Verify include paths and libraries
    echo.
    pause
    exit /b 1
)

REM Find executable
set EXECUTABLE_PATH=
if exist "%EXECUTABLE_NAME%.exe" (
    set EXECUTABLE_PATH=%EXECUTABLE_NAME%.exe
) else if exist "%CONFIG%\%EXECUTABLE_NAME%.exe" (
    set EXECUTABLE_PATH=%CONFIG%\%EXECUTABLE_NAME%.exe
) else if exist "Debug\%EXECUTABLE_NAME%.exe" (
    set EXECUTABLE_PATH=Debug\%EXECUTABLE_NAME%.exe
) else if exist "Release\%EXECUTABLE_NAME%.exe" (
    set EXECUTABLE_PATH=Release\%EXECUTABLE_NAME%.exe
)

if "%EXECUTABLE_PATH%"=="" (
    echo.
    echo ERROR: Executable not found!
    echo Expected: %EXECUTABLE_NAME%.exe
    echo.
    echo Searching for executables...
    for /r . %%f in (*.exe) do echo Found: %%f
    pause
    exit /b 1
)

REM Go back to project root
cd ..

REM Display success
echo.
echo ========================================
echo Build completed successfully!
echo ========================================
echo Configuration: %CONFIG%
echo Executable: %BUILD_DIR%\%EXECUTABLE_PATH%
echo Build Time: %date% %time%
echo ========================================
echo.

REM Copy resources if they don't exist in build directory
if not exist "%BUILD_DIR%\resources" (
    echo Copying resources to build directory...
    xcopy /E /I /Y "resources" "%BUILD_DIR%\resources"
)

REM Run application if requested
if "%RUN_AFTER_BUILD%"=="true" (
    echo Starting %PROJECT_NAME%...
    echo.
    "%BUILD_DIR%\%EXECUTABLE_PATH%"
    
    if errorlevel 1 (
        echo.
        echo Application exited with error code: %errorlevel%
    ) else (
        echo.
        echo Application exited successfully.
    )
) else (
    echo To run the application:
    echo "%BUILD_DIR%\%EXECUTABLE_PATH%"
    echo.
    echo Or use: build_and_run.bat %CONFIG% --run
)

echo.
pause
exit /b 0

:show_help
echo.
echo ========================================
echo %PROJECT_NAME% Build Script Help
echo ========================================
echo.
echo Usage: build_and_run.bat [CONFIG] [OPTIONS]
echo.
echo CONFIGURATIONS:
echo   Debug     - Debug build with symbols
echo   Release   - Release build optimized
echo   Shipping  - Same as Release
echo.
echo OPTIONS:
echo   --clean   - Clean previous builds before building
echo   --run     - Run the application after building
echo   --verbose - Show detailed build output
echo   --help    - Show this help message
echo.
echo EXAMPLES:
echo   build_and_run.bat Debug
echo   build_and_run.bat Release --clean --run
echo   build_and_run.bat Debug --verbose
echo   build_and_run.bat Shipping --clean --run
echo.
echo Default: Debug build
echo.
pause
exit /b 0
