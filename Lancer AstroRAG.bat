@echo off
setlocal
cd /d "%~dp0"
title AstroRAG
if not exist ".venv\Scripts\python.exe" (
    echo L'environnement Python est absent. Suivez la preparation dans README.md.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" "scripts\launch_chat.py"
if errorlevel 1 pause
