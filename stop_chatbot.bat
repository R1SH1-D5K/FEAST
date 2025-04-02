@echo off
echo Stopping Recipe Chatbot...

REM Kill all python processes related to Rasa
taskkill /F /IM "python.exe" /FI "WINDOWTITLE eq *rasa*" > nul 2>&1
taskkill /F /IM "python.exe" /FI "WINDOWTITLE eq *Starting Action Server*" > nul 2>&1
taskkill /F /IM "python.exe" /FI "WINDOWTITLE eq *Starting Rasa Server*" > nul 2>&1
taskkill /F /IM "python.exe" /FI "WINDOWTITLE eq *Starting Rasa Shell*" > nul 2>&1

REM Kill any processes using our ports
netstat -ano | findstr :5055 | findstr LISTENING > nul
if not errorlevel 1 (
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5055 ^| findstr LISTENING') do taskkill /F /PID %%a
)
netstat -ano | findstr :5006 | findstr LISTENING > nul
if not errorlevel 1 (
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5006 ^| findstr LISTENING') do taskkill /F /PID %%a
)

REM Close command windows by title
taskkill /F /FI "WINDOWTITLE eq Starting Action Server*" > nul 2>&1
taskkill /F /FI "WINDOWTITLE eq Starting Rasa Server*" > nul 2>&1
taskkill /F /FI "WINDOWTITLE eq Starting Rasa Shell*" > nul 2>&1
taskkill /F /FI "WINDOWTITLE eq Bot loaded.*" > nul 2>&1

REM Close any remaining command windows with "rasa" in the title
taskkill /F /FI "WINDOWTITLE eq *rasa*" > nul 2>&1

REM Wait a moment to ensure everything is closed
timeout /t 2 > nul

echo Chatbot stopped successfully!
echo All terminal windows should be closed.
pause 