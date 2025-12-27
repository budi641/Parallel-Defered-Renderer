@echo off
REM Phase 3: Extended Demo
REM Runs the fault-tolerant rendering demo for 120 seconds with multiple faults

echo ============================================================
echo Phase 3: Extended Fault-Tolerant Rendering Demo
echo ============================================================
echo.
echo Configuration:
echo   - 2 replicas
echo   - 120 second duration
echo   - 15 requests/second
echo   - Fault injection at 30s, 60s, and 90s
echo.

call venv\Scripts\activate.bat 2>nul

python demo.py --duration 120 --rate 15 --faults 30,60,90 --output-dir demo_output_extended

echo.
echo Demo complete! Results saved to demo_output_extended/
pause
