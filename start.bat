@echo off
echo AI Background Remover - Professional Tool
echo ==========================================

echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo Starting AI Background Remover...
python start.py

pause