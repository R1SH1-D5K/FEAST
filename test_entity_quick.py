import os
import json
import logging
from rasa.core.agent import Agent
import asyncio

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test queries focusing on problematic cases
TEST_QUERIES = [
    "Vegetarian lasagna recipe",
    "Recipes with tomatoes and basil",
    "Gluten-free desserts without nuts",
    "I need a quick pasta dish",
    "What Italian desserts can I make?"
]

async def test_entities():
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
    
    # Test each query
    for query in TEST_QUERIES:
        logger.info(f"\nTesting query: '{query}'")
        result = await agent.parse_message(query)
        
        # Display entities
        entities = result.get('entities', [])
        logger.info(f"Extracted entities: {entities}")
        
        # Display intent
        intent = result.get('intent', {}).get('name')
        confidence = result.get('intent', {}).get('confidence')
        logger.info(f"Detected intent: {intent} (confidence: {confidence:.2f})")

if __name__ == "__main__":
    logger.info("Starting targeted entity test...")
    asyncio.run(test_entities())
    logger.info("Testing complete!") 