@echo off
REM ========================================
REM Parallel-Deferred-Renderer Quick Build
REM ========================================

echo Building Parallel-Deferred-Renderer...

REM Quick Debug build
if exist "build_Debug" rmdir /s /q "build_Debug"
mkdir "build_Debug"
cd "build_Debug"

cmake .. -DCMAKE_BUILD_TYPE=Debug
cmake --build . --config Debug --parallel

if errorlevel 1 (
    echo Build failed!
    pause
    exit /b 1
)

cd ..

echo Build completed! Running application...
"build_Debug\Parallel-Deferred-Renderer\Debug\Parallel-Deferred-Renderer.exe"

pause
