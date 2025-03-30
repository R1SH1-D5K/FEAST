@echo off
echo Starting Recipe Chatbot...

echo.
echo Step 1: Kill any existing Rasa processes
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5005') do (
    echo Killing process %%a
    taskkill /F /PID %%a 2>nul
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5006') do (
    echo Killing process %%a
    taskkill /F /PID %%a 2>nul
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000') do (
    echo Killing process %%a
    taskkill /F /PID %%a 2>nul
)

echo.
echo Step 2: Train the model
call rasa train --force || exit /b 1

echo.
echo Step 3: Start the action server
start cmd /k "title Rasa Action Server && cd %cd% && rasa run actions"

echo.
echo Step 4: Start the Rasa server
start cmd /k "title Rasa Server && cd %cd% && rasa run --enable-api --cors \"*\" --debug"

echo.
echo Step 5: Choose an option:
echo 1. Start the shell
echo 2. Start the API server
echo 3. Run conversation tests
set /p option="Enter option (1-3): "

if "%option%"=="1" (
    echo Starting the shell...
    start cmd /k "title Rasa Shell && cd %cd% && rasa shell --endpoints endpoints.yml"
) else if "%option%"=="2" (
    echo Starting the API server...
    start cmd /k "title API Server && cd %cd% && python api.py"
) else if "%option%"=="3" (
    echo Running conversation tests...
    start cmd /k "title Conversation Tests && cd %cd% && python test_conversations.py"
) else (
    echo Invalid option. Starting the shell by default...
    start cmd /k "title Rasa Shell && cd %cd% && rasa shell --endpoints endpoints.yml"
)

echo.
echo All components started!
echo.
echo You can now:
echo - Test entity extraction with: python test_entity_quick.py
echo - Test full conversations with: python test_conversations.py
echo - Interact with the chatbot in the Rasa Shell window
echo - Connect to the API at http://localhost:8000/chat
echo. 