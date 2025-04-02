import os
import sys
import logging
import asyncio
import requests
import subprocess
import time
from pymongo import MongoClient

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ChecklistItem:
    def __init__(self, name, check_function, critical=True):
        self.name = name
        self.check_function = check_function
        self.critical = critical
        self.status = None
        self.message = None
    
    async def run(self):
        try:
            result = await self.check_function()
            if isinstance(result, tuple):
                self.status = result[0]
                self.message = result[1]
            else:
                self.status = result
                self.message = "OK" if result else "Failed"
        except Exception as e:
            self.status = False
            self.message = str(e)
        
        return self.status

async def check_model_exists():
    """Check if a trained model exists"""
    models_dir = "./models"
    if not os.path.exists(models_dir):
        return False, "Models directory not found"
    
    model_files = [f for f in os.listdir(models_dir) if f.endswith('.tar.gz')]
    if not model_files:
        return False, "No model found in models directory"
    
    latest_model = os.path.join(models_dir, sorted(model_files)[-1])
    return True, f"Found model: {latest_model}"

async def check_mongodb_connection():
    """Check MongoDB connection"""
    try:
        from pymongo import MongoClient
        import os
        
        mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
        client.server_info()  # Will raise exception if cannot connect
        
        # Check if recipes collection exists and has data
        db = client["recipeDB"]
        collection = db["recipes"]
        count = collection.count_documents({})
        
        if count == 0:
            return False, "MongoDB connected but recipes collection is empty"
        
        return True, f"MongoDB connected, found {count} recipes"
    except Exception as e:
        return False, f"MongoDB connection failed: {e}"

async def check_api_server():
    """Check if API server is running"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code == 200:
            return True, "API server is running"
        else:
            return False, f"API server returned status code {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, "API server is not running"
    except Exception as e:
        return False, f"Error checking API server: {e}"

async def check_action_server():
    """Check if Rasa Action server is running"""
    try:
        response = requests.get("http://localhost:5055/health", timeout=2)
        if response.status_code == 200:
            return True, "Rasa Action server is running"
        else:
            return False, f"Rasa Action server returned status code {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, "Rasa Action server is not running"
    except Exception as e:
        return False, f"Error checking Rasa Action server: {e}"

async def check_required_files():
    """Check if all required files exist"""
    required_files = [
        "actions/actions.py",
        "api.py",
        "recipe_db.py",
        "config.yml",
        "domain.yml",
        "endpoints.yml",
        "credentials.yml",
        "components/spell_checker.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        return False, f"Missing files: {', '.join(missing_files)}"
    else:
        return True, "All required files exist"

async def check_entity_extraction():
    """Run a quick entity extraction test"""
    try:
        result = subprocess.run(["python", "test_entity_quick.py"], capture_output=True, text=True)
        if result.returncode == 0:
            return True, "Entity extraction test passed"
        else:
            return False, f"Entity extraction test failed: {result.stderr}"
    except Exception as e:
        return False, f"Error running entity extraction test: {e}"

async def run_checklist():
    """Run all checklist items"""
    checklist = [
        ChecklistItem("Model exists", check_model_exists, critical=True),
        ChecklistItem("MongoDB connection", check_mongodb_connection, critical=False),
        ChecklistItem("Required files", check_required_files, critical=True),
        ChecklistItem("API server", check_api_server, critical=False),
        ChecklistItem("Action server", check_action_server, critical=False),
        ChecklistItem("Entity extraction", check_entity_extraction, critical=True)
    ]
    
    logger.info("Running pre-demo checklist...")
    
    all_passed = True
    critical_failed = False
    
    for item in checklist:
        logger.info(f"Checking: {item.name}...")
        status = await item.run()
        
        if status:
            logger.info(f"✅ {item.name}: {item.message}")
        else:
            all_passed = False
            if item.critical:
                critical_failed = True
                logger.error(f"❌ CRITICAL: {item.name}: {item.message}")
            else:
                logger.warning(f"⚠️ WARNING: {item.name}: {item.message}")
    
    if all_passed:
        logger.info("\n✅ ALL CHECKS PASSED! Ready for demo.")
        return True
    elif critical_failed:
        logger.error("\n❌ CRITICAL CHECKS FAILED! Not ready for demo.")
        return False
    else:
        logger.warning("\n⚠️ SOME NON-CRITICAL CHECKS FAILED. Demo may work with limitations.")
        return True

if __name__ == "__main__":
    success = asyncio.run(run_checklist())
    sys.exit(0 if success else 1) 