import asyncio
import logging
from rasa.core.agent import Agent
import os

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test conversations for context retention
CONTEXT_TEST_CONVERSATIONS = [
    # Test adding preferences incrementally
    [
        "I want Italian recipes",
        "Make it vegetarian",
        "Something quick",
        "Without garlic"
    ],
    # Test overriding preferences
    [
        "Show me chicken recipes",
        "Actually, make it vegetarian instead",
        "What Italian options do you have?"
    ]
]

async def test_context_retention():
    """Test that context (slots) is retained properly across messages"""
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
    
    for i, conversation in enumerate(CONTEXT_TEST_CONVERSATIONS):
        logger.info(f"\nTesting context retention - Conversation {i+1}:")
        sender_id = f"context_test_{i}"
        
        for message in conversation:
            logger.info(f"User: {message}")
            response = await agent.handle_text(message, sender_id=sender_id)
            
            # Extract and log the tracker state after each message
            tracker = agent.tracker_store.get_or_create_tracker(sender_id)
            slots = {key: value for key, value in tracker.current_slot_values().items() 
                    if key in ["diet", "cuisine", "ingredient", "course", "time", "taste", "exclude_ingredient"]}
            
            logger.info(f"Bot: {[msg.get('text') for msg in response if msg.get('text')]}")
            logger.info(f"Current slots: {slots}")

if __name__ == "__main__":
    logger.info("Starting context retention test...")
    asyncio.run(test_context_retention())
    logger.info("Testing complete!") 