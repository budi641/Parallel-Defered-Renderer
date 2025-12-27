@echo off
REM Phase 3: High Availability Rendering Service
REM Setup Script for Windows

echo ============================================================
echo Phase 3: High Availability Setup
echo ============================================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.8+
    exit /b 1
)

echo [1/4] Creating virtual environment...
if not exist "venv" (
    python -m venv venv
)

echo [2/4] Activating virtual environment...
call venv\Scripts\activate.bat

echo [3/4] Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt

echo [4/4] Generating Protocol Buffer code...
python generate_proto.py

echo.
echo ============================================================
echo Setup complete!
echo ============================================================
echo.
echo To run the demo:
echo   1. Activate environment: venv\Scripts\activate.bat
echo   2. Run demo: python demo.py
echo.
echo Or use the run scripts:
echo   - run_demo.bat          (standard demo)
echo   - run_demo_extended.bat (extended with more faults)
echo   - run_spark_demo.bat    (with Spark streaming)
echo.
