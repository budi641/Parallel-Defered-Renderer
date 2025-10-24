@echo off
setlocal enabledelayedexpansion

REM ========================================
REM Parallel-Deferred-Renderer Build Script
REM ========================================

REM Default configuration (can be overridden by command line argument)
set CONFIG=Debug
set PROJECT_NAME=Parallel-Deferred-Renderer

REM Check for command line arguments
if "%1"=="Debug" set CONFIG=Debug
if "%1"=="Release" set CONFIG=Release
if "%1"=="Shipping" set CONFIG=Release
if "%1"=="debug" set CONFIG=Debug
if "%1"=="release" set CONFIG=Release
if "%1"=="shipping" set CONFIG=Release

REM Display current configuration
echo.
echo ========================================
echo Building %PROJECT_NAME% in %CONFIG% mode
echo ========================================
echo.

REM Set build directory
set BUILD_DIR=build_%CONFIG%
set EXECUTABLE_NAME=%PROJECT_NAME%

REM Clean previous build if it exists
if exist "%BUILD_DIR%" (
    echo Cleaning previous %CONFIG% build...
    rmdir /s /q "%BUILD_DIR%"
)

REM Create build directory
echo Creating build directory...
mkdir "%BUILD_DIR%"
cd "%BUILD_DIR%"

REM Configure CMake
echo.
echo Configuring CMake for %CONFIG% build...
if "%CONFIG%"=="Debug" (
    cmake .. -DCMAKE_BUILD_TYPE=Debug -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
) else (
    cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
)

REM Check if CMake configuration was successful
if errorlevel 1 (
    echo.
    echo ERROR: CMake configuration failed!
    echo Please check your CMake installation and dependencies.
    pause
    exit /b 1
)

REM Build the project
echo.
echo Building %PROJECT_NAME%...
cmake --build . --config %CONFIG% --parallel

REM Check if build was successful
if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    echo Please check the error messages above.
    pause
    exit /b 1
)

REM Find the executable
set EXECUTABLE_PATH=
if exist "%EXECUTABLE_NAME%.exe" (
    set EXECUTABLE_PATH=%EXECUTABLE_NAME%.exe
) else if exist "%CONFIG%\%EXECUTABLE_NAME%.exe" (
    set EXECUTABLE_PATH=%CONFIG%\%EXECUTABLE_NAME%.exe
) else if exist "Debug\%EXECUTABLE_NAME%.exe" (
    set EXECUTABLE_PATH=Debug\%EXECUTABLE_NAME%.exe
) else if exist "Release\%EXECUTABLE_NAME%.exe" (
    set EXECUTABLE_PATH=Release\%EXECUTABLE_NAME%.exe
) else (
    echo.
    echo ERROR: Executable not found!
    echo Expected: %EXECUTABLE_NAME%.exe
    echo Searched in: current directory, %CONFIG%\, Debug\, Release\
    echo.
    echo Available files:
    dir /b *.exe 2>nul
    dir /b %CONFIG%\*.exe 2>nul
    dir /b Debug\*.exe 2>nul
    dir /b Release\*.exe 2>nul
    pause
    exit /b 1
)

REM Go back to project root
cd ..

REM Display success message
echo.
echo ========================================
echo Build completed successfully!
echo ========================================
echo Configuration: %CONFIG%
echo Executable: %BUILD_DIR%\%EXECUTABLE_PATH%
echo.

REM Ask if user wants to run the application
set /p RUN_APP="Do you want to run the application? (Y/N): "
if /i "%RUN_APP%"=="Y" (
    echo.
    echo Starting %PROJECT_NAME%...
    echo.
    "%BUILD_DIR%\%EXECUTABLE_PATH%"
    
    REM Check if application ran successfully
    if errorlevel 1 (
        echo.
        echo Application exited with error code: %errorlevel%
    ) else (
        echo.
        echo Application exited successfully.
    )
) else (
    echo.
    echo Build completed. You can run the application manually:
    echo "%BUILD_DIR%\%EXECUTABLE_PATH%"
)

echo.
echo ========================================
echo Build script completed.
echo ========================================
pause
