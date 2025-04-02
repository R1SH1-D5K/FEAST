@echo off
echo Setting up Recipe Chatbot...

REM Set conda path
set CONDA_PATH=C:\anaconda3

REM Remove existing environment if it exists
call "%CONDA_PATH%\Scripts\conda.exe" env remove -n rasa -y

REM Create new environment
call "%CONDA_PATH%\Scripts\conda.exe" create -n rasa python=3.10 -y

REM Activate environment and install dependencies
call "%CONDA_PATH%\Scripts\activate.bat" rasa
pip install rasa==3.6.21
pip install fastapi==0.95.1
pip install uvicorn==0.22.0
pip install pymongo==4.3.3
pip install python-dotenv==1.0.0

REM Train the model
rasa train

echo Setup complete! You can now run the chatbot using run_chatbot.bat
pause 