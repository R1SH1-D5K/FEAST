from rasa_sdk.executor import ActionExecutor
import sys
import os
import logging
import importlib.util
import subprocess

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Explicitly import the actions.py file
logger.info("Attempting to import actions...")
try:
    # Get the full path to actions.py
    actions_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "actions.py")
    logger.info(f"Looking for actions.py at: {actions_path}")
    
    # Check if the file exists
    if not os.path.exists(actions_path):
        raise FileNotFoundError(f"actions.py not found at {actions_path}")
    
    logger.info("actions.py found, starting action server...")
    
    # Use subprocess to run the standard Rasa action server
    subprocess.run(["rasa", "run", "actions", "--port", "5055"])
    
except Exception as e:
    logger.error(f"Error: {str(e)}")
    raise 