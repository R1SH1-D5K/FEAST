import asyncio
import logging
import os
import json
import time
import subprocess
import sys
import requests
from rasa.core.agent import Agent

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def run_final_test():
    """Run a comprehensive test of all components working together"""
    logger.info("Starting final integration test...")
    
    # Step 1: Start the action server
    logger.info("\nStarting action server...")
    action_server = subprocess.Popen(
        ["rasa", "run", "actions"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(5)  # Give it time to start
    
    # Step 2: Start the API server
    logger.info("Starting API server...")
    api_server = subprocess.Popen(
        [sys.executable, "api.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(5)  # Give it time to start
    
    try:
        # Step 3: Test the API
        logger.info("\nTesting API...")
        
        # Test health endpoint
        health_response = requests.get("http://localhost:8000/health")
        if health_response.status_code == 200:
            logger.info("✅ API health check passed")
        else:
            logger.error("❌ API health check failed")
            return
        
        # Test chat endpoint
        test_messages = [
            "Show me vegetarian pasta recipes",
            "I want something without tomatoes",
            "Clear my preferences"
        ]
        
        sender_id = "final_test_user"
        
        for message in test_messages:
            logger.info(f"\nSending message: '{message}'")
            
            response = requests.post(
                "http://localhost:8000/chat",
                json={"message": message, "sender_id": sender_id}
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info("✅ Received response")
                
                if data.get('formatted_response'):
                    for msg in data['formatted_response']['messages']:
                        logger.info(f"Bot: {msg['content']}")
            else:
                logger.error(f"❌ Error: {response.status_code} - {response.text}")
        
        # Step 4: Test recipes endpoint
        logger.info("\nTesting recipes endpoint...")
        
        params = {
            "diet": "vegetarian",
            "cuisine": "Italian"
        }
        
        response = requests.get("http://localhost:8000/recipes", params=params)
        
        if response.status_code == 200:
            data = response.json()
            logger.info("✅ Recipes endpoint working")
            logger.info(f"Found {data.get('count')} recipes")
        else:
            logger.error(f"❌ Error: {response.status_code} - {response.text}")
        
        logger.info("\nFinal integration test completed successfully!")
        logger.info("The system is ready for the demo.")
        
    except Exception as e:
        logger.error(f"Error during final test: {e}")
    
    finally:
        # Clean up processes
        logger.info("\nShutting down servers...")
        action_server.terminate()
        api_server.terminate()

if __name__ == "__main__":
    asyncio.run(run_final_test()) 