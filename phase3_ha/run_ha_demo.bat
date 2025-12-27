@echo off
REM ============================================================
REM Phase 3: Run HA Demo with 2 Replicas and Failover
REM ============================================================

echo.
echo ============================================================
echo   Running HA Demo (2 Replicas + Automatic Failover)
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

echo [INFO] Starting HA demo with 2 replicas...
echo [INFO] This will:
echo        - Start Replica 1 on port 50051
echo        - Start Replica 2 on port 50052
echo        - Test rendering requests
echo        - Simulate failure and verify failover
echo.

python demo_native_ha.py

echo.
echo Demo complete!
pause
