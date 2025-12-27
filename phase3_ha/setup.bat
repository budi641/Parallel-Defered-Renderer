@echo off
REM ============================================================
REM Phase 3: Fault-Tolerant Distributed Renderer - Setup Script
REM ============================================================
REM This script sets up the Python environment and dependencies

echo.
echo ============================================================
echo   Phase 3 Setup Script
echo ============================================================
echo.

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

echo [OK] Python found
python --version

REM Navigate to phase3_ha directory
cd /d "%~dp0"

REM Install dependencies
echo.
echo [INFO] Installing Python dependencies...
pip install -r requirements.txt

if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo [OK] Dependencies installed successfully!
echo.
echo ============================================================
echo   Setup Complete! Available Commands:
echo ============================================================
echo.
echo   1. Run HA Demo (2 replicas + failover test):
echo      python demo_native_ha.py
echo.
echo   2. Run Performance Analysis (120 seconds):
echo      python performance_analysis.py --duration 120 --rate 30
echo.
echo   3. Run Spark Streaming:
echo      python grpc_spark_streaming.py
echo.
echo   4. Generate PDF Report:
echo      python generate_report_pdf.py
echo.
echo ============================================================
echo.
pause
