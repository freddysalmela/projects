@echo off
cd /d "%~dp0"
venv\Scripts\python.exe -m mycroft.main
if errorlevel 1 (
    echo.
    echo Gaia stopped with an error. The message above says why.
    pause
)
