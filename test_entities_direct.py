import os
import sys
import json
import logging
import glob
import asyncio
from rasa.engine.storage.local_model_storage import LocalModelStorage
from rasa.engine.graph import ExecutionContext
from rasa.nlu.classifiers.diet_classifier import DIETClassifier
from rasa.shared.nlu.training_data.message import Message
from rasa.model import get_latest_model

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_interpreter():
    """Load the latest trained model"""
    model_directory = "./models"
    model_path = get_latest_model(model_directory)
    if not model_path:
        logger.error("No model found in ./models directory")
        return None
    
    logger.info(f"Loading model from {model_path}")
    
    # For newer Rasa versions, we'll use a simpler approach
    # that doesn't rely on the specific interpreter class
    return model_path

async def parse_with_model(model_path, text):
    """Parse text using the model directly"""
    from rasa.core.agent import Agent
    agent = Agent.load(model_path)
    result = await agent.parse_message(text)
    return result

def load_test_data(file_path='test_queries.json'):
    """Load test queries from JSON file"""
    try:
        with open(file_path, 'r') as f:
            test_data = json.load(f)
        logger.info(f"Loaded {len(test_data)} test cases from {file_path}")
        return test_data
    except Exception as e:
        logger.error(f"Error loading test data: {str(e)}")
        return []

async def test_entity_extraction():
    """Test entity extraction on test queries"""
    # Load model path
    model_path = load_interpreter()
    if not model_path:
        return
    
    # Load test data
    test_data = load_test_data()
    if not test_data:
        return
    
    # Run tests
    results = []
    for test_case in test_data:
        text = test_case['text']
        expected = test_case['expected_entities']
        
        # Parse with model
        parsed = await parse_with_model(model_path, text)
        extracted = parsed.get('entities', [])
        
        logger.info(f"\nQuery: '{text}'")
        logger.info(f"Extracted entities: {extracted}")
        
        # Compare expected vs extracted
        for exp in expected:
            found = False
            matched_value = None
            
            for ext in extracted:
                if ext['entity'] == exp['entity']:
                    # Check if values match (case-insensitive)
                    if ext['value'].lower() == exp['value'].lower():
                        found = True
                        matched_value = ext['value']
                        break
                    # If entity type matches but value doesn't, still record the extracted value
                    matched_value = ext['value']
            
            results.append({
                'text': text,
                'entity_type': exp['entity'],
                'expected_value': exp['value'],
                'extracted_value': matched_value,
                'found': found
            })
    
    # Calculate accuracy
    total = len(results)
    correct = sum(1 for r in results if r['found'])
    accuracy = correct / total if total > 0 else 0
    
    logger.info(f"\nOverall accuracy: {accuracy:.2%} ({correct}/{total})")
    
    # Accuracy by entity type
    entity_types = set(r['entity_type'] for r in results)
    logger.info("\nAccuracy by entity type:")
    for entity_type in entity_types:
        type_results = [r for r in results if r['entity_type'] == entity_type]
        type_correct = sum(1 for r in type_results if r['found'])
        type_total = len(type_results)
        type_accuracy = type_correct / type_total if type_total > 0 else 0
        logger.info(f"{entity_type}: {type_accuracy:.2%} ({type_correct}/{type_total})")
    
    # Examples of failures
    failures = [r for r in results if not r['found']]
    if failures:
        logger.info("\nExamples of missed entities:")
        for failure in failures[:5]:  # Show first 5 failures
            logger.info(f"Query: '{failure['text']}'")
            logger.info(f"Expected: {failure['entity_type']} = {failure['expected_value']}")
            if failure['extracted_value']:
                logger.info(f"Extracted: {failure['extracted_value']}")
            else:
                logger.info("No entity of this type was extracted")
            logger.info("---")

if __name__ == "__main__":
    # Run the async function
    asyncio.run(test_entity_extraction()) 