@echo off
title Local AI Workspace Shutdown
echo ==========================================
echo    Stopping Local AI Workspace (Windows)
echo ==========================================
echo.

cd /d "%~dp0"
docker compose down

echo.
echo [SUCCESS] Workspace stopped safely. Your computer's RAM has been freed.
echo.
pause
