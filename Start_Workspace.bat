@echo off
title Local AI Workspace Launcher
echo ==========================================
echo    Starting Local AI Workspace (Windows)
echo ==========================================
echo.
echo Checking for Docker Desktop...

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
echo Your tools are ready.
echo Open your terminal for Aider, or browser for Khoj/IronClaw.
echo.
echo Note: To use the IronClaw agent on Windows, open a WSL terminal, paste this exact command, and press Enter:
echo export DATABASE_URL="postgres://silo_admin:silo_password@127.0.0.1:5432/ironsilo_vault" ^&^& export OPENAI_API_BASE="http://127.0.0.1:8001/api/v1" ^&^& export OPENAI_API_KEY="local-sandbox" ^&^& ironclaw start
echo.
pause