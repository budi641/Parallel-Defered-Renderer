@echo off
REM Phase 3: Start Replica Servers Manually
REM Use this to start the rendering service replicas for testing

echo ============================================================
echo Starting Rendering Service Replicas
echo ============================================================
echo.

call venv\Scripts\activate.bat 2>nul

echo Starting Replica 1 on port 50051...
start "Replica 1" cmd /k "python rendering_server.py --port 50051 --replica-id replica-1"

timeout /t 2 >nul

echo Starting Replica 2 on port 50052...
start "Replica 2" cmd /k "python rendering_server.py --port 50052 --replica-id replica-2"

echo.
echo Replicas started in separate windows.
echo.
echo To test manually:
echo   python -c "from rendering_client import create_client; c = create_client(); print(c.health_check())"
echo.
pause
