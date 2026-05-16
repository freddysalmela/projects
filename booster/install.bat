@echo off
echo Installing Booster...

python -m venv venv
venv\Scripts\python.exe -m pip install --quiet --upgrade pip
venv\Scripts\python.exe -m pip install pyaudio
venv\Scripts\python.exe -m pip install -e .

if not exist .env (
    copy .env.example .env
    echo.
    echo Edit .env and add your ANTHROPIC_API_KEY, then run booster.bat
    notepad .env
) else (
    echo.
    echo Already set up. Run booster.bat to start.
)
pause
