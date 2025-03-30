import asyncio
import json
import logging
from rasa.core.agent import Agent
import os

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test conversation flows
TEST_CONVERSATIONS = [
    # Simple recipe query
    [
        "Show me vegetarian pasta recipes",
        "I want something without tomatoes",
        "Clear my preferences",
        "What Italian desserts can I make?"
    ],
    # Complex query with multiple entities
    [
        "I need quick gluten-free breakfast ideas",
        "Do you have any with eggs?",
        "I prefer something sweet"
    ],
    # Edge cases
    [
        "I don't eat dairy",
        "Show me recipes ready in under 30 minutes",
        "I want something spicy but not too hot"
    ]
]

async def test_conversations():
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
    
    # Test each conversation flow
    for i, conversation in enumerate(TEST_CONVERSATIONS):
        logger.info(f"\n\nTesting conversation flow {i+1}:")
        
        # Create a unique sender ID for this conversation
        sender_id = f"test_user_{i}"
        
        for message in conversation:
            logger.info(f"\nUser: {message}")
            response = await agent.handle_text(message, sender_id=sender_id)
            logger.info(f"Bot: {json.dumps(response, indent=2)}")
            
            # Add a small delay to make output more readable
            await asyncio.sleep(0.5)

if __name__ == "__main__":
    logger.info("Starting conversation flow tests...")
    asyncio.run(test_conversations())
    logger.info("Testing complete!") 