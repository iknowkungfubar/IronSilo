@echo off
title Local AI Workspace Launcher
echo ==========================================
echo    Starting Local AI Workspace (Windows)
echo ==========================================
echo.
echo Checking for Docker...

cd /d "%~dp0"
docker compose up -d

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to start. Please make sure Docker Desktop is open and running!
    pause
    exit /b %errorlevel%
)

echo.
echo [SUCCESS] Your AI Workspace is now running in the background!
echo You can now open this folder in VS Code.
echo.
pause
