@echo off
echo Starting Recipe Chatbot...

REM Kill any existing Rasa processes
taskkill /F /IM "python.exe" /FI "WINDOWTITLE eq *rasa*" > nul 2>&1
taskkill /F /IM "python.exe" /FI "WINDOWTITLE eq *Starting Action Server*" > nul 2>&1
taskkill /F /IM "python.exe" /FI "WINDOWTITLE eq *Starting Rasa Server*" > nul 2>&1
taskkill /F /IM "python.exe" /FI "WINDOWTITLE eq *Starting Rasa Shell*" > nul 2>&1

REM Kill any processes using our ports
netstat -ano | findstr :5005 | findstr LISTENING > nul
if not errorlevel 1 (
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5005 ^| findstr LISTENING') do taskkill /F /PID %%a
)

REM Wait for processes to fully terminate
timeout /t 5

REM Set conda path
set CONDA_PATH=C:\anaconda3

REM Activate conda environment
call "%CONDA_PATH%\Scripts\activate.bat" rasa

REM First, train the model to ensure it's up to date
python -m rasa train

REM Start the action server on port 5055
start cmd /k "python -m rasa run actions --port 5055"

REM Wait for action server to start
timeout /t 10

REM Start the Rasa server on port 5006
start cmd /k "python -m rasa run --enable-api --cors '*' --port 5006 --model models"

REM Wait for Rasa server to start
timeout /t 10

REM Start the shell with model path
start cmd /k "python -m rasa shell --model models --endpoints endpoints.yml"

echo.
echo Chatbot is running! You can now interact with it.
echo To stop, close all terminal windows or run stop_chatbot.bat
pause 