import subprocess
import sys
import os
import platform
import time
import shutil

def setup_environment():
    print("Setting up Recipe Chatbot environment...")
    
    # Deactivate virtual environment if it's active
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("Deactivating current virtual environment...")
        if platform.system() == "Windows":
            subprocess.run(["deactivate"], shell=True)
        else:
            subprocess.run(["deactivate"], shell=True)
        time.sleep(2)  # Give some time for processes to close
    
    # Remove existing virtual environment
    if os.path.exists("venv"):
        print("Removing existing virtual environment...")
        try:
            # Try using shutil first (more reliable)
            shutil.rmtree("venv", ignore_errors=True)
        except Exception as e:
            print(f"Warning: Could not remove directory completely: {e}")
            # If shutil fails, try system commands
            try:
                if platform.system() == "Windows":
                    os.system('taskkill /F /IM python.exe')  # Force close any Python processes
                    time.sleep(2)
                    os.system('rd /s /q venv')
                else:
                    os.system('rm -rf venv')
            except Exception as e:
                print(f"Warning: Could not remove directory using system commands: {e}")
        
        # Wait a moment to ensure cleanup is complete
        time.sleep(2)
    
    print("Creating virtual environment...")
    subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
    
    # Set up paths based on OS
    if platform.system() == "Windows":
        python_path = os.path.join("venv", "Scripts", "python.exe")
        pip_path = os.path.join("venv", "Scripts", "pip.exe")
        activate_path = os.path.join("venv", "Scripts", "activate.ps1")
    else:
        python_path = os.path.join("venv", "bin", "python")
        pip_path = os.path.join("venv", "bin", "pip")
        activate_path = os.path.join("venv", "bin", "activate")
    
    # Wait for the virtual environment to be ready
    time.sleep(2)
    
    # Activate virtual environment
    if os.path.exists(activate_path):
        print("Activating virtual environment...")
        try:
            if platform.system() == "Windows":
                # Use cmd.exe to activate the environment
                activate_command = f"call {os.path.join('venv', 'Scripts', 'activate.bat')} && set"
                subprocess.run(activate_command, shell=True, check=True)
            else:
                subprocess.run(f"source {activate_path}", shell=True, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Warning: Could not activate virtual environment: {e}")
    
    # Upgrade pip
    print("Upgrading pip...")
    subprocess.run([python_path, "-m", "pip", "install", "--upgrade", "pip"], check=True)
    
    # Install dependencies one by one to handle conflicts better
    print("Installing dependencies...")
    dependencies = [
        "wheel",  # Add wheel first to help with binary packages
        "setuptools>=41.0.0",  # Ensure recent setuptools
        "pyyaml>=5.3.1,<6.0",
        "scikit-learn==1.1.3",
        "numpy==1.24.3",
        "pandas==2.0.1",
        "fastapi==0.95.1",
        "uvicorn==0.22.0",
        "pymongo==4.3.3",
        "python-dotenv==1.0.0",
        "requests==2.29.0",
        "rasa==3.6.2"
    ]
    
    for dep in dependencies:
        print(f"Installing {dep}...")
        try:
            subprocess.run([pip_path, "install", dep], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error installing {dep}: {str(e)}")
            sys.exit(1)
    
    # Train the model
    print("Training Rasa model...")
    try:
        rasa_cmd = os.path.join("venv", "Scripts", "rasa.exe") if platform.system() == "Windows" else os.path.join("venv", "bin", "rasa")
        subprocess.run([rasa_cmd, "train"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error training model: {str(e)}")
        sys.exit(1)
    
    print("\nSetup completed successfully!")
    print("You can now run the chatbot using 'run_chatbot.bat'")

if __name__ == "__main__":
    try:
        setup_environment()
    except Exception as e:
        print(f"Error during setup: {str(e)}")
        sys.exit(1) 