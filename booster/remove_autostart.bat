@echo off
rem Stops Gaia from starting when you log in to Windows.
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
del "%STARTUP%\Gaia Assistant.bat" >nul 2>&1
del "%STARTUP%\Gaia Assistant.lnk" >nul 2>&1
schtasks /delete /tn "Gaia Assistant" /f >nul 2>&1
echo Autostart removed.
pause
