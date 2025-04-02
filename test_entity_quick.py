import logging
import json
from rasa.nlu.model import Interpreter
import os

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test cases for quick validation
QUICK_TEST_CASES = [
    {
        "text": "I want vegetarian Italian pasta recipes",
        "expected": [
            {"entity": "diet", "value": "vegetarian"},
            {"entity": "cuisine", "value": "Italian"},
            {"entity": "ingredient", "value": "pasta"}
        ]
    },
    {
        "text": "Show me quick Mexican dishes without onions",
        "expected": [
            {"entity": "time", "value": "quick"},
            {"entity": "cuisine", "value": "Mexican"},
            {"entity": "exclude_ingredient", "value": "onions"}
        ]
    },
    {
        "text": "I need gluten-free desserts",
        "expected": [
            {"entity": "diet", "value": "gluten-free"},
            {"entity": "course", "value": "desserts"}
        ]
    }
]

def main():
    """Run a quick entity extraction test"""
    logger.info("Starting quick entity extraction test...")
    
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
    
    # Test each case
    all_passed = True
    for i, test_case in enumerate(QUICK_TEST_CASES):
        logger.info(f"\nTesting case {i+1}: '{test_case['text']}'")
        
        # Parse the text
        result = interpreter.parse(test_case["text"])
        
        # Extract entities
        extracted_entities = []
        for entity in result.get("entities", []):
            extracted_entities.append({
                "entity": entity["entity"],
                "value": entity["value"]
            })
        
        # Check if all expected entities were extracted
        expected_entities = test_case["expected"]
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
            all_passed = False
        else:
            logger.info(f"✅ Passed: All expected entities extracted")
    
    if all_passed:
        logger.info("\nAll quick entity extraction tests passed!")
        return True
    else:
        logger.error("\nSome entity extraction tests failed!")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 