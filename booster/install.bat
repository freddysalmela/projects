@echo off
echo Installing Mycroft...

python -m venv venv
venv\Scripts\python.exe -m pip install --quiet --upgrade pip
venv\Scripts\python.exe -m pip install --quiet -r requirements.txt

if not exist .env (
    copy .env.example .env
    echo.
    echo Open .env in Notepad and add your ANTHROPIC_API_KEY, then run mycroft.bat
    notepad .env
) else (
    echo.
    echo Done. Run mycroft.bat to start Mycroft.
)
pause
