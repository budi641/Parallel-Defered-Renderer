@echo off
REM Phase 3: Spark Streaming Demo
REM Runs the demo with micro-batch processing (Spark Structured Streaming pattern)

echo ============================================================
echo Phase 3: Spark Streaming Rendering Demo
echo ============================================================
echo.
echo Configuration:
echo   - 2 replicas
echo   - 60 second duration
echo   - 5 second micro-batch interval
echo   - 5 requests/second
echo.

call venv\Scripts\activate.bat 2>nul

python demo.py --mode spark --duration 60 --rate 5 --batch-interval 5 --output-dir demo_output_spark

echo.
echo Demo complete! Results saved to demo_output_spark/
pause
