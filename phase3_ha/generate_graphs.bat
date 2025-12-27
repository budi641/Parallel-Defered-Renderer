@echo off
REM Phase 3: Generate Performance Graphs
REM Creates visualizations from demo output

echo ============================================================
echo Generating Performance Graphs
echo ============================================================
echo.

call venv\Scripts\activate.bat 2>nul

if not exist "demo_output\time_series.csv" (
    echo ERROR: No demo output found.
    echo Please run the demo first: run_demo.bat
    exit /b 1
)

pip install matplotlib -q

python visualize.py --input-dir demo_output --output-dir demo_output

echo.
echo Graphs generated in demo_output/
echo.
echo Generated files:
echo   - latency_graph.png
echo   - throughput_graph.png
echo   - combined_graph.png
echo   - success_rate_graph.png
echo.
pause
