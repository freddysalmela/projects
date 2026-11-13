@echo off
setlocal
rem Makes Gaia start when you log in to Windows. Double-click to run. No admin needed.

set "BOOSTER=%~dp0"
if "%BOOSTER:~-1%"=="\" set "BOOSTER=%BOOSTER:~0,-1%"
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "TARGET=%STARTUP%\Gaia Assistant.bat"

if not exist "%BOOSTER%\venv\Scripts\python.exe" (
    echo Could not find venv\Scripts\python.exe in:
    echo   %BOOSTER%
    echo Run install.bat first, then run this again.
    echo.
    pause
    exit /b 1
)

if not exist "%STARTUP%" (
    echo Could not find your Startup folder:
    echo   %STARTUP%
    echo.
    pause
    exit /b 1
)

rem Remove what earlier versions of this setup may have left behind, so Gaia does not start twice.
del "%STARTUP%\Gaia Assistant.lnk" >nul 2>&1
schtasks /delete /tn "Gaia Assistant" /f >nul 2>&1

> "%TARGET%" echo @echo off
>> "%TARGET%" echo rem Starts Gaia at login. Created by setup_autostart.bat. Delete this file to turn autostart off.
>> "%TARGET%" echo rem The wait gives Windows time to bring up the network and sound devices.
>> "%TARGET%" echo timeout /t 20 /nobreak ^>nul
>> "%TARGET%" echo cd /d "%BOOSTER%"
>> "%TARGET%" echo call gaia_autostart.bat

echo.
if exist "%TARGET%" (
    echo Done. Gaia will start about 20 seconds after you log in.
    echo.
    echo Created: %TARGET%
    echo To turn autostart off, run remove_autostart.bat or delete that file.
) else (
    echo FAILED: could not create
    echo   %TARGET%
    echo Your antivirus may be blocking changes to the Startup folder.
)
echo.
pause
