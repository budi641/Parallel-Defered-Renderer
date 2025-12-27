@echo off
REM ============================================================
REM Phase 3: Run Performance Analysis
REM ============================================================

echo.
echo ============================================================
echo   Running Performance Analysis
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

REM Parse arguments or use defaults
set DURATION=120
set RATE=30

if not "%1"=="" set DURATION=%1
if not "%2"=="" set RATE=%2

echo [INFO] Configuration:
echo        Duration: %DURATION% seconds
echo        Rate: %RATE% requests/second
echo.
echo [INFO] This will:
echo        - Start 2 renderer replicas
echo        - Generate load for %DURATION% seconds
echo        - Inject failures periodically
echo        - Collect metrics (latency, throughput, recovery time)
echo        - Generate graphs and CSV files
echo.

python performance_analysis.py --duration %DURATION% --rate %RATE%

echo.
echo ============================================================
echo   Results saved to: performance_results\
echo ============================================================
echo.
echo Output files:
echo   - request_events_*.csv    (all request data)
echo   - window_metrics_*.csv    (per-second stats)
echo   - failure_events_*.csv    (failure/recovery times)
echo   - performance_graphs_*.png (latency/throughput plots)
echo   - recovery_times_*.png    (recovery time chart)
echo   - summary_*.json          (aggregate stats)
echo.
pause
