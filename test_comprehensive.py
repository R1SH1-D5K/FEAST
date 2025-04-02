import asyncio
import logging
import os
import json
import requests
import time
from rasa.core.agent import Agent
from rasa.nlu.model import Interpreter
import random
import uuid

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Comprehensive test cases
COMPREHENSIVE_TEST_CASES = [
    # Basic queries
    {
        "category": "Basic Queries",
        "tests": [
            {"text": "Show me vegetarian recipes", "expected_entities": [{"entity": "diet", "value": "vegetarian"}]},
            {"text": "I want Italian food", "expected_entities": [{"entity": "cuisine", "value": "Italian"}]},
            {"text": "Recipes with chicken", "expected_entities": [{"entity": "ingredient", "value": "chicken"}]}
        ]
    },
    
    # Complex queries
    {
        "category": "Complex Queries",
        "tests": [
            {
                "text": "I need quick gluten-free breakfast ideas without eggs",
                "expected_entities": [
                    {"entity": "time", "value": "quick"},
                    {"entity": "diet", "value": "gluten-free"},
                    {"entity": "course", "value": "breakfast"},
                    {"entity": "exclude_ingredient", "value": "eggs"}
                ]
            },
            {
                "text": "Show me spicy vegetarian Mexican dishes ready in under 30 minutes",
                "expected_entities": [
                    {"entity": "taste", "value": "spicy"},
                    {"entity": "diet", "value": "vegetarian"},
                    {"entity": "cuisine", "value": "Mexican"},
                    {"entity": "time", "value": "under 30 minutes"}
                ]
            }
        ]
    },
    
    # Misspellings and typos
    {
        "category": "Misspellings and Typos",
        "tests": [
            {"text": "Show me vegitarian recipes", "expected_entities": [{"entity": "diet", "value": "vegetarian"}]},
            {"text": "I want itallian food", "expected_entities": [{"entity": "cuisine", "value": "Italian"}]},
            {"text": "Recipies with chiken", "expected_entities": [{"entity": "ingredient", "value": "chicken"}]}
        ]
    },
    
    # Conversational context
    {
        "category": "Conversational Context",
        "conversation": [
            {"text": "I want vegetarian recipes", "expected_entities": [{"entity": "diet", "value": "vegetarian"}]},
            {"text": "Show me Italian options", "expected_entities": [{"entity": "cuisine", "value": "Italian"}]},
            {"text": "I prefer pasta dishes", "expected_entities": [{"entity": "ingredient", "value": "pasta"}]},
            {"text": "Actually, make it vegan instead", "expected_entities": [{"entity": "diet", "value": "vegan"}]}
        ]
    },
    
    # Edge cases
    {
        "category": "Edge Cases",
        "tests": [
            {"text": "I want a recipe", "expected_entities": []},
            {"text": "What can I cook?", "expected_entities": []},
            {"text": "I want vegan recipes with chicken", "expected_entities": [
                {"entity": "diet", "value": "vegan"},
                {"entity": "ingredient", "value": "chicken"}
            ]}
        ]
    },
    
    # Nutritional queries
    {
        "category": "Nutritional Queries",
        "tests": [
            {"text": "Show me low-calorie recipes", "expected_entities": [{"entity": "nutritional", "value": "low-calorie"}]},
            {"text": "I need high-protein vegetarian meals", "expected_entities": [
                {"entity": "nutritional", "value": "high-protein"},
                {"entity": "diet", "value": "vegetarian"}
            ]},
            {"text": "Recipes under 500 calories", "expected_entities": [{"entity": "nutritional", "value": "under 500 calories"}]}
        ]
    }
]

async def test_entity_extraction():
    """Test entity extraction with comprehensive test cases"""
    logger.info("Starting comprehensive entity extraction test...")
    
    # Find the latest model
    models_dir = "./models"
    model_files = [f for f in os.listdir(models_dir) if f.endswith('.tar.gz')]
    if not model_files:
        logger.error("No model found in models directory")
        return False
    
    latest_model = os.path.join(models_dir, sorted(model_files)[-1])
    logger.info(f"Using model: {latest_model}")
    
    # Load the interpreter
    interpreter = Interpreter.load(latest_model)
    logger.info("Model loaded successfully")
    
    # Test each category
    overall_success = True
    
    for category in COMPREHENSIVE_TEST_CASES:
        logger.info(f"\n\n=== Testing Category: {category['category']} ===")
        
        if "tests" in category:
            # Individual tests
            for test in category["tests"]:
                success = await test_single_message(interpreter, test["text"], test["expected_entities"])
                if not success:
                    overall_success = False
        
        elif "conversation" in category:
            # Conversation flow
            success = await test_conversation(category["conversation"])
            if not success:
                overall_success = False
    
    if overall_success:
        logger.info("\n\nAll comprehensive tests passed!")
    else:
        logger.error("\n\nSome tests failed!")
    
    return overall_success

async def test_single_message(interpreter, text, expected_entities):
    """Test entity extraction for a single message"""
    logger.info(f"\nTesting: '{text}'")
    
    # Parse the text
    result = interpreter.parse(text)
    
    # Extract entities
    extracted_entities = []
    for entity in result.get("entities", []):
        extracted_entities.append({
            "entity": entity["entity"],
            "value": entity["value"]
        })
    
    # Check if all expected entities were extracted
    missing_entities = []
    
    for expected in expected_entities:
        found = False
        for extracted in extracted_entities:
            if (expected["entity"] == extracted["entity"] and 
                expected["value"].lower() in extracted["value"].lower()):
                found = True
                break
        
        if not found:
            missing_entities.append(expected)
    
    if missing_entities:
        logger.error(f"❌ Failed: Missing entities: {missing_entities}")
        logger.error(f"Extracted: {extracted_entities}")
        return False
    else:
        logger.info(f"✅ Passed: All expected entities extracted")
        return True

async def test_conversation(conversation):
    """Test entity extraction in a conversation context"""
    logger.info("\nTesting conversation flow...")
    
    # Load the agent for conversation context
    models_dir = "./models"
    model_files = [f for f in os.listdir(models_dir) if f.endswith('.tar.gz')]
    latest_model = os.path.join(models_dir, sorted(model_files)[-1])
    
    agent = await Agent.load(latest_model)
    
    # Generate a unique sender ID for this test
    sender_id = f"test_user_{uuid.uuid4()}"
    
    # Process each message in the conversation
    for i, message in enumerate(conversation):
        text = message["text"]
        expected_entities = message["expected_entities"]
        
        logger.info(f"\nConversation step {i+1}: '{text}'")
        
        # Process the message
        response = await agent.handle_text(text, sender_id=sender_id)
        
        # Get the tracker to check entities
        tracker = agent.tracker_store.get_or_create_tracker(sender_id)
        latest_message = tracker.latest_message
        
        # Extract entities from the latest message
        extracted_entities = []
        for entity in latest_message.get("entities", []):
            extracted_entities.append({
                "entity": entity["entity"],
                "value": entity["value"]
            })
        
        # Check if all expected entities were extracted
        missing_entities = []
        
        for expected in expected_entities:
            found = False
            for extracted in extracted_entities:
                if (expected["entity"] == extracted["entity"] and 
                    expected["value"].lower() in extracted["value"].lower()):
                    found = True
                    break
            
            if not found:
                missing_entities.append(expected)
        
        if missing_entities:
            logger.error(f"❌ Failed: Missing entities: {missing_entities}")
            logger.error(f"Extracted: {extracted_entities}")
            return False
        else:
            logger.info(f"✅ Passed: All expected entities extracted")
    
    return True

async def test_api_endpoints():
    """Test API endpoints"""
    logger.info("\n\n=== Testing API Endpoints ===")
    
    base_url = "http://localhost:8000"
    
    # Test health endpoint
    try:
        logger.info("\nTesting health endpoint...")
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            logger.info("✅ Health endpoint working")
        else:
            logger.error(f"❌ Health endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Health endpoint error: {e}")
        return False
    
    # Test chat endpoint
    try:
        logger.info("\nTesting chat endpoint...")
        data = {
            "message": "Show me vegetarian recipes",
            "sender_id": f"test_user_{uuid.uuid4()}"
        }
        response = requests.post(f"{base_url}/chat", json=data)
        if response.status_code == 200:
            logger.info("✅ Chat endpoint working")
        else:
            logger.error(f"❌ Chat endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Chat endpoint error: {e}")
        return False
    
    # Test recipes endpoint
    try:
        logger.info("\nTesting recipes endpoint...")
        params = {"diet": "vegetarian", "cuisine": "Italian"}
        response = requests.get(f"{base_url}/recipes", params=params)
        if response.status_code == 200:
            logger.info("✅ Recipes endpoint working")
        else:
            logger.error(f"❌ Recipes endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Recipes endpoint error: {e}")
        return False
    
    # Test clear_preferences endpoint
    try:
        logger.info("\nTesting clear_preferences endpoint...")
        data = {"sender_id": f"test_user_{uuid.uuid4()}"}
        response = requests.post(f"{base_url}/clear_preferences", json=data)
        if response.status_code == 200:
            logger.info("✅ Clear preferences endpoint working")
        else:
            logger.error(f"❌ Clear preferences endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Clear preferences endpoint error: {e}")
        return False
    
    logger.info("\n✅ All API endpoints working")
    return True

async def test_error_handling():
    """Test error handling scenarios"""
    logger.info("\n\n=== Testing Error Handling ===")
    
    # Load the agent
    models_dir = "./models"
    model_files = [f for f in os.listdir(models_dir) if f.endswith('.tar.gz')]
    latest_model = os.path.join(models_dir, sorted(model_files)[-1])
    
    agent = await Agent.load(latest_model)
    
    # Test scenarios
    error_scenarios = [
        {
            "name": "Empty message",
            "message": "",
            "sender_id": f"test_user_{uuid.uuid4()}"
        },
        {
            "name": "Very long message",
            "message": "I want a recipe " + "very " * 100 + "long",
            "sender_id": f"test_user_{uuid.uuid4()}"
        },
        {
            "name": "Special characters",
            "message": "I want a recipe with @#$%^&*()_+",
            "sender_id": f"test_user_{uuid.uuid4()}"
        },
        {
            "name": "Non-English characters",
            "message": "I want a recipe with 你好 привет こんにちは",
            "sender_id": f"test_user_{uuid.uuid4()}"
        }
    ]
    
    for scenario in error_scenarios:
        logger.info(f"\nTesting error scenario: {scenario['name']}")
        
        try:
            # Process the message
            response = await agent.handle_text(scenario["message"], sender_id=scenario["sender_id"])
            logger.info(f"✅ Handled without crashing: {response}")
        except Exception as e:
            logger.error(f"❌ Failed to handle: {e}")
            return False
    
    logger.info("\n✅ All error scenarios handled without crashing")
    return True

async def run_all_tests():
    """Run all tests"""
    logger.info("Starting comprehensive testing...")
    
    # Run entity extraction tests
    entity_success = await test_entity_extraction()
    
    # Run API endpoint tests
    api_success = await test_api_endpoints()
    
    # Run error handling tests
    error_success = await test_error_handling()
    
    # Overall result
    if entity_success and api_success and error_success:
        logger.info("\n\n✅ ALL TESTS PASSED!")
        return True
    else:
        logger.error("\n\n❌ SOME TESTS FAILED!")
        return False

if __name__ == "__main__":
    asyncio.run(run_all_tests()) 