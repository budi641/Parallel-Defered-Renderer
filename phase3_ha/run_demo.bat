@echo off
REM Phase 3: Standard Demo
REM Runs the fault-tolerant rendering demo for 60 seconds

echo ============================================================
echo Phase 3: Fault-Tolerant Rendering Demo
echo ============================================================
echo.
echo Configuration:
echo   - 2 replicas
echo   - 60 second duration
echo   - 10 requests/second
echo   - Fault injection at 20s and 40s
echo.

call venv\Scripts\activate.bat 2>nul

python demo.py --duration 60 --rate 10 --faults 20,40

echo.
echo Demo complete! Results saved to demo_output/
pause
