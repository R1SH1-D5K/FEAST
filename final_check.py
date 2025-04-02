import os
import sys
import logging
import subprocess
import requests
import time
import asyncio
from rasa.core.agent import Agent

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_model_exists():
    """Check if a trained model exists"""
    models_dir = "./models"
    if not os.path.exists(models_dir):
        logger.error("Models directory not found")
        return False
    
    model_files = [f for f in os.listdir(models_dir) if f.endswith('.tar.gz')]
    if not model_files:
        logger.error("No trained model found. Please run 'rasa train' first.")
        return False
    
    logger.info(f"Found trained model: {sorted(model_files)[-1]}")
    return True

def check_required_files():
    """Check if all required files exist"""
    required_files = [
        "actions/actions.py",
        "data/nlu.yml",
        "data/stories.yml",
        "data/rules.yml",
        "domain.yml",
        "config.yml",
        "endpoints.yml",
        "api.py",
        "recipe_db.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        logger.error(f"Missing required files: {', '.join(missing_files)}")
        return False
    
    logger.info("All required files exist")
    return True

def check_mongodb_connection():
    """Check if MongoDB is accessible"""
    try:
        from pymongo import MongoClient
        client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)
        client.server_info()  # Will raise an exception if cannot connect
        logger.info("MongoDB connection successful")
        return True
    except Exception as e:
        logger.warning(f"MongoDB connection failed: {e}")
        logger.warning("The chatbot will fall back to sample recipes")
        return False

async def check_rasa_functionality():
    """Check if Rasa can load the model and process messages"""
    try:
        # Load the agent
        agent = Agent.load("./models")
        logger.info("Rasa model loaded successfully")
        
        # Test a simple message
        response = await agent.handle_text("Hello", sender_id="test_user")
        if response:
            logger.info("Rasa can process messages successfully")
            return True
        else:
            logger.error("Rasa failed to process a test message")
            return False
    except Exception as e:
        logger.error(f"Error testing Rasa functionality: {e}")
        return False

def check_api_server():
    """Check if the API server can be started"""
    try:
        # Start the API server in a subprocess
        process = subprocess.Popen(
            [sys.executable, "api.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for the server to start
        time.sleep(5)
        
        # Check if the server is running
        try:
            response = requests.get("http://localhost:8000/health")
            if response.status_code == 200:
                logger.info("API server started successfully")
                result = True
            else:
                logger.error(f"API server health check failed: {response.status_code}")
                result = False
        except Exception as e:
            logger.error(f"Error connecting to API server: {e}")
            result = False
        
        # Kill the process
        process.terminate()
        return result
    except Exception as e:
        logger.error(f"Error starting API server: {e}")
        return False

async def run_final_check():
    """Run all checks to ensure the system is ready for the demo"""
    logger.info("Running final integration check...")
    
    checks = [
        ("Model exists", check_model_exists()),
        ("Required files exist", check_required_files()),
        ("MongoDB connection", check_mongodb_connection()),
        ("Rasa functionality", await check_rasa_functionality()),
        ("API server", check_api_server())
    ]
    
    # Print results
    logger.info("\nFinal Check Results:")
    all_passed = True
    for name, result in checks:
        status = "PASS" if result else "FAIL"
        if not result:
            all_passed = False
        logger.info(f"{name}: {status}")
    
    if all_passed:
        logger.info("\n✅ All checks passed! The system is ready for the demo.")
    else:
        logger.warning("\n⚠️ Some checks failed. Please address the issues before the demo.")

if __name__ == "__main__":
    asyncio.run(run_final_check()) 