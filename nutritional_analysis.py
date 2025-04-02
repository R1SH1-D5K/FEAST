import logging
import re
import json
import os
from typing import Dict, List, Any, Optional

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load nutritional database
try:
    with open("data/nutritional_data.json", "r") as f:
        NUTRITIONAL_DATABASE = json.load(f)
    logger.info(f"Loaded nutritional database with {len(NUTRITIONAL_DATABASE)} ingredients")
except Exception as e:
    logger.warning(f"Could not load nutritional database: {e}")
    NUTRITIONAL_DATABASE = {}

# Nutritional requirement patterns
NUTRITIONAL_PATTERNS = {
    "calories": [
        r"under (\d+) calories",
        r"less than (\d+) calories",
        r"(\d+) calories or less",
        r"low[- ]calorie",
        r"low in calories"
    ],
    "protein": [
        r"at least (\d+)g? of protein",
        r"high[- ]protein",
        r"rich in protein",
        r"protein[- ]rich"
    ],
    "carbs": [
        r"low[- ]carb",
        r"under (\d+)g? of carbs",
        r"less than (\d+)g? carbs",
        r"keto"
    ],
    "fat": [
        r"low[- ]fat",
        r"less than (\d+)g? of fat",
        r"heart[- ]healthy"
    ]
}

def extract_nutritional_requirements(text: str) -> Dict[str, Any]:
    """Extract nutritional requirements from text"""
    requirements = {}
    
    # Convert to lowercase for matching
    text_lower = text.lower()
    
    # Check for calorie requirements
    for pattern in NUTRITIONAL_PATTERNS["calories"]:
        matches = re.search(pattern, text_lower)
        if matches and len(matches.groups()) > 0:
            try:
                requirements["calories"] = {"max": int(matches.group(1))}
            except (ValueError, IndexError):
                requirements["calories"] = {"max": 500}  # Default low-calorie threshold
        elif matches:
            requirements["calories"] = {"max": 500}  # Default low-calorie threshold
    
    # Check for protein requirements
    for pattern in NUTRITIONAL_PATTERNS["protein"]:
        matches = re.search(pattern, text_lower)
        if matches and len(matches.groups()) > 0:
            try:
                requirements["protein"] = {"min": int(matches.group(1))}
            except (ValueError, IndexError):
                requirements["protein"] = {"min": 20}  # Default high-protein threshold
        elif matches:
            requirements["protein"] = {"min": 20}  # Default high-protein threshold
    
    # Check for carb requirements
    for pattern in NUTRITIONAL_PATTERNS["carbs"]:
        matches = re.search(pattern, text_lower)
        if matches and len(matches.groups()) > 0:
            try:
                requirements["carbs"] = {"max": int(matches.group(1))}
            except (ValueError, IndexError):
                requirements["carbs"] = {"max": 20}  # Default low-carb threshold
        elif matches:
            requirements["carbs"] = {"max": 20}  # Default low-carb threshold
            
            # Special case for keto
            if "keto" in text_lower:
                requirements["carbs"] = {"max": 10}  # Stricter for keto
                requirements["fat"] = {"min": 70}  # High fat for keto
    
    # Check for fat requirements
    for pattern in NUTRITIONAL_PATTERNS["fat"]:
        matches = re.search(pattern, text_lower)
        if matches and len(matches.groups()) > 0:
            try:
                requirements["fat"] = {"max": int(matches.group(1))}
            except (ValueError, IndexError):
                requirements["fat"] = {"max": 15}  # Default low-fat threshold
        elif matches:
            requirements["fat"] = {"max": 15}  # Default low-fat threshold
    
    return requirements

def analyze_recipe_nutrition(recipe: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze nutritional content of a recipe"""
    if not NUTRITIONAL_DATABASE:
        return {}
    
    # Get ingredients
    ingredients = recipe.get("ingredients", [])
    if not ingredients:
        return {}
    
    # Initialize nutritional totals
    nutrition = {
        "calories": 0,
        "protein": 0,
        "carbs": 0,
        "fat": 0,
        "fiber": 0,
        "sugar": 0,
        "sodium": 0
    }
    
    # Process each ingredient
    for ingredient in ingredients:
        # Try to match ingredient with database
        matched = False
        for db_ingredient, data in NUTRITIONAL_DATABASE.items():
            if db_ingredient.lower() in ingredient.lower():
                # Estimate quantity (simplified)
                quantity_match = re.search(r'(\d+)', ingredient)
                quantity = 1
                if quantity_match:
                    try:
                        quantity = int(quantity_match.group(1))
                    except ValueError:
                        pass
                
                # Add nutritional values (scaled by quantity)
                for nutrient, value in data.items():
                    if nutrient in nutrition:
                        nutrition[nutrient] += value * quantity
                
                matched = True
                break
        
        if not matched:
            logger.debug(f"Could not find nutritional data for: {ingredient}")
    
    # Add per-serving information if available
    servings = recipe.get("servings", 4)  # Default to 4 servings
    try:
        servings = int(servings)
    except (ValueError, TypeError):
        servings = 4
    
    nutrition["per_serving"] = {
        nutrient: round(value / servings, 1) 
        for nutrient, value in nutrition.items()
    }
    
    return nutrition

def meets_nutritional_requirements(recipe: Dict[str, Any], requirements: Dict[str, Any]) -> bool:
    """Check if recipe meets nutritional requirements"""
    if not requirements:
        return True
    
    # Analyze recipe nutrition
    nutrition = analyze_recipe_nutrition(recipe)
    if not nutrition:
        return True  # If we can't analyze, give benefit of the doubt
    
    # Use per-serving values
    per_serving = nutrition.get("per_serving", {})
    
    # Check each requirement
    for nutrient, req in requirements.items():
        if nutrient not in per_serving:
            continue
        
        value = per_serving[nutrient]
        
        if "min" in req and value < req["min"]:
            return False
        
        if "max" in req and value > req["max"]:
            return False
    
    return True

def get_nutritional_summary(recipe: Dict[str, Any]) -> str:
    """Get a human-readable nutritional summary for a recipe"""
    nutrition = analyze_recipe_nutrition(recipe)
    if not nutrition or not nutrition.get("per_serving"):
        return ""
    
    per_serving = nutrition["per_serving"]
    
    summary = "\n\n**Nutritional Information (per serving):**\n"
    summary += f"• Calories: {per_serving.get('calories', 'N/A')} kcal\n"
    summary += f"• Protein: {per_serving.get('protein', 'N/A')}g\n"
    summary += f"• Carbohydrates: {per_serving.get('carbs', 'N/A')}g\n"
    summary += f"• Fat: {per_serving.get('fat', 'N/A')}g\n"
    
    if "fiber" in per_serving:
        summary += f"• Fiber: {per_serving.get('fiber', 'N/A')}g\n"
    
    if "sugar" in per_serving:
        summary += f"• Sugar: {per_serving.get('sugar', 'N/A')}g\n"
    
    if "sodium" in per_serving:
        summary += f"• Sodium: {per_serving.get('sodium', 'N/A')}mg\n"
    
    return summary 