@echo off
REM ============================================================
REM Phase 3: Run All Demos Sequentially
REM ============================================================

echo.
echo ============================================================
echo   Phase 3: Complete Demo Suite
echo ============================================================
echo.
echo This script will run:
echo   1. HA Demo (failover test)
echo   2. Performance Analysis (120 seconds)
echo   3. Generate PDF Report
echo.
echo Press any key to start or Ctrl+C to cancel...
pause >nul

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

echo.
echo ============================================================
echo   Step 1/3: HA Demo
echo ============================================================
echo.
python demo_native_ha.py
if errorlevel 1 (
    echo [ERROR] HA Demo failed
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Step 2/3: Performance Analysis (120 seconds)
echo ============================================================
echo.
python performance_analysis.py --duration 120 --rate 30
if errorlevel 1 (
    echo [ERROR] Performance analysis failed
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Step 3/3: Generate PDF Report
echo ============================================================
echo.
python generate_report_pdf.py
if errorlevel 1 (
    echo [WARNING] PDF generation had issues
)

echo.
echo ============================================================
echo   All Demos Complete!
echo ============================================================
echo.
echo Results:
echo   - Performance data: performance_results\
echo   - PDF Report: Phase3_Report.pdf
echo.

if exist "Phase3_Report.pdf" (
    echo Opening report...
    start "" "Phase3_Report.pdf"
)

pause
