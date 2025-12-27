@echo off
REM ============================================================
REM Phase 3: Generate PDF Report
REM ============================================================

echo.
echo ============================================================
echo   Generating PDF Report
echo ============================================================
echo.

cd /d "%~dp0"

REM Check for performance results
if not exist "performance_results" (
    echo [WARNING] No performance_results directory found!
    echo [INFO] Run performance analysis first to generate metrics:
    echo        python performance_analysis.py --duration 120 --rate 30
    echo.
)

echo [INFO] Generating PDF report...
echo [INFO] This will create Phase3_Report.pdf with:
echo        - Architecture overview
echo        - Implementation details
echo        - Performance graphs
echo        - Metrics analysis
echo.

python generate_report_pdf.py

if exist "Phase3_Report.pdf" (
    echo.
    echo ============================================================
    echo   Report generated: Phase3_Report.pdf
    echo ============================================================
    echo.
    echo Opening report...
    start "" "Phase3_Report.pdf"
) else (
    echo [ERROR] Failed to generate report
)

pause
