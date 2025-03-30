import os
import sys
import logging
import subprocess
import time
import asyncio
import requests

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def run_pre_demo_checklist():
    """Run through a checklist before the demo"""
    logger.info("Running pre-demo checklist...")
    
    # Check 1: Verify model is trained and up-to-date
    logger.info("\n1. Checking model...")
    models_dir = "./models"
    if not os.path.exists(models_dir) or not [f for f in os.listdir(models_dir) if f.endswith('.tar.gz')]:
        logger.error("❌ No trained model found! Run 'rasa train' before the demo.")
    else:
        model_files = [f for f in os.listdir(models_dir) if f.endswith('.tar.gz')]
        latest_model = sorted(model_files)[-1]
        logger.info(f"✅ Found model: {latest_model}")
    
    # Check 2: Verify all services can start
    logger.info("\n2. Testing service startup...")
    
    # Start action server
    logger.info("Starting action server...")
    action_server = subprocess.Popen(
        ["rasa", "run", "actions"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(5)  # Give it time to start
    
    # Start API server
    logger.info("Starting API server...")
    api_server = subprocess.Popen(
        [sys.executable, "api.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(5)  # Give it time to start
    
    # Check if API is responding
    try:
        response = requests.get("http://localhost:8000/health")
        if response.status_code == 200:
            logger.info("✅ API server is running")
        else:
            logger.error("❌ API server health check failed")
    except:
        logger.error("❌ API server is not responding")
    
    # Clean up processes
    action_server.terminate()
    api_server.terminate()
    
    # Check 3: Run a quick entity extraction test
    logger.info("\n3. Running quick entity extraction test...")
    test_process = subprocess.Popen(
        [sys.executable, "test_entity_quick.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = test_process.communicate()
    if test_process.returncode == 0:
        logger.info("✅ Entity extraction test passed")
    else:
        logger.error("❌ Entity extraction test failed")
        logger.error(stderr.decode())
    
    # Check 4: Verify demo script works
    logger.info("\n4. Verifying demo script...")
    if os.path.exists("demo_script.py"):
        logger.info("✅ Demo script is ready")
    else:
        logger.error("❌ Demo script not found")
    
    logger.info("\nPre-demo checklist complete!")
    logger.info("\nReminder: During the demo, run these commands in separate terminals:")
    logger.info("1. rasa run actions")
    logger.info("2. python api.py")
    logger.info("3. python demo_script.py --interactive")

if __name__ == "__main__":
    asyncio.run(run_pre_demo_checklist()) 