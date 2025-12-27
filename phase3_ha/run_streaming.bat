@echo off
REM ============================================================
REM Phase 3: Run Spark Streaming Demo
REM ============================================================

echo.
echo ============================================================
echo   Running Spark Streaming Demo
echo ============================================================
echo.

cd /d "%~dp0"

REM Check if renderer exists
if not exist "..\build_Debug\Debug\Parallel-Deferred-Renderer.exe" (
    echo [ERROR] Renderer not found!
    echo Please build the renderer first:
    echo   cd ..
    echo   build_and_run.bat Debug
    pause
    exit /b 1
)

echo [INFO] Starting Spark streaming demo...
echo [INFO] This will:
echo        - Start gRPC rendering server
echo        - Stream frames at ~30 FPS
echo        - Process frames in micro-batches
echo        - Display streaming statistics
echo.
echo [NOTE] Press Ctrl+C to stop streaming
echo.

python grpc_spark_streaming.py

echo.
echo Streaming complete!
pause
