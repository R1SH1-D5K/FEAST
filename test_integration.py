import asyncio
import logging
import os
import json
import requests
from rasa.core.agent import Agent

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test scenarios
TEST_SCENARIOS = [
    {
        "name": "Entity Extraction Test",
        "function": "test_entity_extraction",
        "description": "Tests the accuracy of entity extraction"
    },
    {
        "name": "Context Retention Test",
        "function": "test_context_retention",
        "description": "Tests that context is maintained across messages"
    },
    {
        "name": "Recipe Search Test",
        "function": "test_recipe_search",
        "description": "Tests the recipe search functionality"
    },
    {
        "name": "API Integration Test",
        "function": "test_api_integration",
        "description": "Tests the API endpoints"
    }
]

async def test_entity_extraction():
    """Run entity extraction test"""
    logger.info("Running entity extraction test...")
    
    # Import and run the entity extraction test
    import test_entity_extraction
    test_entity_extraction.main()
    
    logger.info("Entity extraction test complete")

async def test_context_retention():
    """Run context retention test"""
    logger.info("Running context retention test...")
    
    # Import and run the context retention test
    import test_context_retention
    await test_context_retention.test_context_retention()
    
    logger.info("Context retention test complete")

async def test_recipe_search():
    """Test recipe search functionality"""
    logger.info("Running recipe search test...")
    
    # Find the latest model
    models_dir = "./models"
    model_files = [f for f in os.listdir(models_dir) if f.endswith('.tar.gz')]
    if not model_files:
        logger.error("No model found in models directory")
        return
    
    latest_model = os.path.join(models_dir, sorted(model_files)[-1])
    logger.info(f"Using model: {latest_model}")
    
    # Load the agent
    agent = Agent.load(latest_model)
    logger.info("Agent loaded successfully")
    
    # Test queries
    test_queries = [
        "Show me vegetarian pasta recipes",
        "I want gluten-free Indian food",
        "Give me some vegan Mexican dishes",
        "I need quick dinner ideas with rice",
        "What can I cook with just tomatoes and basil?"
    ]
    
    for query in test_queries:
        logger.info(f"\nTesting query: '{query}'")
        response = await agent.handle_text(query, sender_id="recipe_search_test")
        
        # Log the response
        for msg in response:
            if msg.get("text"):
                logger.info(f"Bot: {msg['text']}")
        
        # Get the current slot values
        tracker = agent.tracker_store.get_or_create_tracker("recipe_search_test")
        slots = {key: value for key, value in tracker.current_slot_values().items() 
                if key in ["diet", "cuisine", "ingredient", "course", "time", "taste", "exclude_ingredient"]}
        
        logger.info(f"Slots: {slots}")
    
    logger.info("Recipe search test complete")

async def test_api_integration():
    """Test API endpoints"""
    logger.info("Running API integration test...")
    
    # Check if API is running
    try:
        health_response = requests.get("http://localhost:8000/health")
        if health_response.status_code != 200:
            logger.error("API is not running. Please start the API server.")
            return
        logger.info("API is running")
    except:
        logger.error("API is not running. Please start the API server.")
        return
    
    # Test chat endpoint
    test_messages = [
        "Show me vegetarian pasta recipes",
        "I want something without tomatoes",
        "Clear my preferences"
    ]
    
    sender_id = "api_test_user"
    
    for message in test_messages:
        logger.info(f"\nTesting message: {message}")
        
        # Send the message to the API
        response = requests.post(
            "http://localhost:8000/chat",
            json={"message": message, "sender_id": sender_id}
        )
        
        # Log the response
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Response status: {data.get('status')}")
            if data.get('formatted_response'):
                for msg in data['formatted_response']['messages']:
                    logger.info(f"Bot: {msg['content']}")
                logger.info(f"Suggestions: {data['formatted_response']['suggestions']}")
            logger.info(f"Slots: {data.get('slots')}")
        else:
            logger.error(f"Error: {response.status_code} - {response.text}")
    
    # Test recipes endpoint
    logger.info("\nTesting recipes endpoint")
    
    params = {
        "diet": "vegetarian",
        "cuisine": "Italian"
    }
    
    response = requests.get("http://localhost:8000/recipes", params=params)
    
    if response.status_code == 200:
        data = response.json()
        logger.info(f"Response status: {data.get('status')}")
        logger.info(f"Number of recipes: {data.get('count')}")
        logger.info(f"Relaxed constraints: {data.get('relaxed_constraints')}")
        if data.get('recipes') and len(data.get('recipes')) > 0:
            logger.info(f"First recipe: {data['recipes'][0].get('name')}")
    else:
        logger.error(f"Error: {response.status_code} - {response.text}")
    
    logger.info("API integration test complete")

async def run_all_tests():
    """Run all tests"""
    logger.info("Starting comprehensive integration tests...")
    
    for scenario in TEST_SCENARIOS:
        logger.info(f"\n{'='*80}")
        logger.info(f"Running {scenario['name']}: {scenario['description']}")
        logger.info(f"{'='*80}\n")
        
        # Call the appropriate test function
        if scenario['function'] == "test_entity_extraction":
            await test_entity_extraction()
        elif scenario['function'] == "test_context_retention":
            await test_context_retention()
        elif scenario['function'] == "test_recipe_search":
            await test_recipe_search()
        elif scenario['function'] == "test_api_integration":
            await test_api_integration()
    
    logger.info("\nAll tests completed!")

if __name__ == "__main__":
    asyncio.run(run_all_tests()) 