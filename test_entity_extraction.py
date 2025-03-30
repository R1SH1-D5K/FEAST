import logging
import json
from rasa.nlu.model import Interpreter
import os
import pandas as pd
from sklearn.metrics import classification_report, accuracy_score
import numpy as np
import re

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test data
TEST_DATA = [
    {"text": "Show me vegetarian lasagna recipes", "entities": [{"entity": "diet", "value": "vegetarian"}, {"entity": "ingredient", "value": "lasagna"}]},
    {"text": "I'm looking for recipes with tomatoes and basil", "entities": [{"entity": "ingredient", "value": "tomatoes"}, {"entity": "ingredient", "value": "basil"}]},
    {"text": "I want gluten-free desserts without nuts", "entities": [{"entity": "diet", "value": "gluten-free"}, {"entity": "course", "value": "desserts"}, {"entity": "exclude_ingredient", "value": "nuts"}]},
    {"text": "I need quick pasta dishes", "entities": [{"entity": "time", "value": "quick"}, {"entity": "ingredient", "value": "pasta"}, {"entity": "course", "value": "dishes"}]},
    {"text": "What Italian desserts can I make?", "entities": [{"entity": "cuisine", "value": "Italian"}, {"entity": "course", "value": "desserts"}]},
    {"text": "Show me some spicy Mexican food", "entities": [{"entity": "taste", "value": "spicy"}, {"entity": "cuisine", "value": "Mexican"}]},
    {"text": "I want to cook something with chicken and rice", "entities": [{"entity": "ingredient", "value": "chicken"}, {"entity": "ingredient", "value": "rice"}]},
    {"text": "Give me vegan breakfast ideas", "entities": [{"entity": "diet", "value": "vegan"}, {"entity": "course", "value": "breakfast"}]},
    {"text": "I need dinner recipes ready in under 30 minutes", "entities": [{"entity": "course", "value": "dinner"}, {"entity": "time", "value": "under 30 minutes"}]},
    {"text": "What can I make that's dairy-free?", "entities": [{"entity": "diet", "value": "dairy-free"}]},
    {"text": "I don't eat onions, what can I cook?", "entities": [{"entity": "exclude_ingredient", "value": "onions"}]},
    {"text": "Show me easy vegetarian recipes for lunch", "entities": [{"entity": "time", "value": "easy"}, {"entity": "diet", "value": "vegetarian"}, {"entity": "course", "value": "lunch"}]},
    {"text": "I want to make a sweet dessert", "entities": [{"entity": "taste", "value": "sweet"}, {"entity": "course", "value": "dessert"}]},
    {"text": "What are some healthy dinner options?", "entities": [{"entity": "diet", "value": "healthy"}, {"entity": "course", "value": "dinner"}]},
    {"text": "I need recipes without garlic", "entities": [{"entity": "exclude_ingredient", "value": "garlic"}]},
    {"text": "Show me Indian curry recipes", "entities": [{"entity": "cuisine", "value": "Indian"}, {"entity": "ingredient", "value": "curry"}]},
    {"text": "What can I cook that's low-carb?", "entities": [{"entity": "diet", "value": "low-carb"}]},
    {"text": "I want to make something with beef", "entities": [{"entity": "ingredient", "value": "beef"}]},
    {"text": "Give me Japanese dinner ideas", "entities": [{"entity": "cuisine", "value": "Japanese"}, {"entity": "course", "value": "dinner"}]},
    {"text": "What are some quick breakfast recipes?", "entities": [{"entity": "time", "value": "quick"}, {"entity": "course", "value": "breakfast"}]}
]

def load_model():
    """Load the latest NLU model"""
    models_dir = "./models"
    model_files = [f for f in os.listdir(models_dir) if f.endswith('.tar.gz')]
    if not model_files:
        logger.error("No model found in models directory")
        return None
    
    latest_model = os.path.join(models_dir, sorted(model_files)[-1])
    logger.info(f"Using model: {latest_model}")
    
    interpreter = Interpreter.load(latest_model)
    return interpreter

def test_entity_extraction(interpreter):
    """Test entity extraction on test data"""
    results = []
    
    for test_case in TEST_DATA:
        text = test_case["text"]
        expected_entities = test_case["entities"]
        
        # Parse with Rasa NLU
        parsed = interpreter.parse(text)
        extracted_entities = parsed.get("entities", [])
        
        # Compare extracted entities with expected entities
        found_entities = []
        for expected in expected_entities:
            found = False
            for extracted in extracted_entities:
                if (extracted["entity"] == expected["entity"] and 
                    expected["value"].lower() in extracted["value"].lower()):
                    found = True
                    break
            found_entities.append(found)
        
        # Calculate accuracy for this test case
        accuracy = sum(found_entities) / len(expected_entities) if expected_entities else 1.0
        
        results.append({
            "text": text,
            "expected": expected_entities,
            "extracted": extracted_entities,
            "accuracy": accuracy
        })
    
    return results

def calculate_metrics(results):
    """Calculate overall metrics"""
    accuracies = [result["accuracy"] for result in results]
    overall_accuracy = sum(accuracies) / len(accuracies)
    
    # Prepare data for classification report
    y_true = []
    y_pred = []
    
    for result in results:
        expected_entities = {(e["entity"], e["value"].lower()) for e in result["expected"]}
        extracted_entities = {(e["entity"], e["value"].lower()) for e in result["extracted"]}
        
        for entity in expected_entities:
            y_true.append(entity)
            if entity in extracted_entities:
                y_pred.append(entity)
            else:
                y_pred.append(("none", "none"))
        
        for entity in extracted_entities:
            if entity not in expected_entities:
                y_true.append(("none", "none"))
                y_pred.append(entity)
    
    return {
        "overall_accuracy": overall_accuracy,
        "entity_accuracy": accuracy_score(y_true, y_pred) if y_true else 0,
        "classification_report": classification_report(y_true, y_pred) if y_true else "No entities found"
    }

def analyze_entity_extraction_errors(results):
    """Analyze entity extraction errors to identify patterns"""
    error_patterns = {
        "missed_entities": [],
        "incorrect_entities": [],
        "entity_type_confusion": []
    }
    
    for result in results:
        if result["accuracy"] < 1.0:
            expected_entities = {(e["entity"], e["value"].lower()) for e in result["expected"]}
            extracted_entities = {(e["entity"], e["value"].lower()) for e in result["extracted"]}
            
            # Find missed entities
            missed = expected_entities - extracted_entities
            for entity in missed:
                error_patterns["missed_entities"].append({
                    "text": result["text"],
                    "missed_entity": entity
                })
            
            # Find incorrect entities
            incorrect = extracted_entities - expected_entities
            for entity in incorrect:
                error_patterns["incorrect_entities"].append({
                    "text": result["text"],
                    "incorrect_entity": entity
                })
            
            # Find entity type confusion (same value, different type)
            for expected in result["expected"]:
                for extracted in result["extracted"]:
                    if (expected["value"].lower() == extracted["value"].lower() and 
                        expected["entity"] != extracted["entity"]):
                        error_patterns["entity_type_confusion"].append({
                            "text": result["text"],
                            "expected": (expected["entity"], expected["value"]),
                            "extracted": (extracted["entity"], extracted["value"])
                        })
    
    return error_patterns

def main():
    """Main function"""
    logger.info("Starting entity extraction test...")
    
    interpreter = load_model()
    if not interpreter:
        return
    
    results = test_entity_extraction(interpreter)
    metrics = calculate_metrics(results)
    
    # Print results
    logger.info(f"Overall accuracy: {metrics['overall_accuracy']:.2%}")
    logger.info(f"Entity accuracy: {metrics['entity_accuracy']:.2%}")
    logger.info(f"Classification report:\n{metrics['classification_report']}")
    
    # Analyze errors
    error_analysis = analyze_entity_extraction_errors(results)
    
    # Print error analysis
    logger.info("\nError Analysis:")
    logger.info(f"Missed entities: {len(error_analysis['missed_entities'])}")
    if error_analysis['missed_entities']:
        for i, error in enumerate(error_analysis['missed_entities'][:5]):  # Show first 5
            logger.info(f"  {i+1}. '{error['text']}' - missed {error['missed_entity']}")
    
    logger.info(f"Incorrect entities: {len(error_analysis['incorrect_entities'])}")
    if error_analysis['incorrect_entities']:
        for i, error in enumerate(error_analysis['incorrect_entities'][:5]):  # Show first 5
            logger.info(f"  {i+1}. '{error['text']}' - incorrect {error['incorrect_entity']}")
    
    logger.info(f"Entity type confusion: {len(error_analysis['entity_type_confusion'])}")
    if error_analysis['entity_type_confusion']:
        for i, error in enumerate(error_analysis['entity_type_confusion'][:5]):  # Show first 5
            logger.info(f"  {i+1}. '{error['text']}' - expected {error['expected']} but got {error['extracted']}")
    
    # Print detailed results
    logger.info("\nDetailed results:")
    for i, result in enumerate(results):
        logger.info(f"\nTest case {i+1}: {result['text']}")
        logger.info(f"Expected entities: {result['expected']}")
        logger.info(f"Extracted entities: {result['extracted']}")
        logger.info(f"Accuracy: {result['accuracy']:.2%}")

if __name__ == "__main__":
    main() 