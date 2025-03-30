import pandas as pd
from pymongo import MongoClient
import os
import logging
import re
from typing import List, Dict, Any, Set

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define non-vegetarian ingredients
NON_VEG_INGREDIENTS: Set[str] = {
    "chicken", "mutton", "beef", "pork", "fish", "shrimp", "prawns", "crab", "egg", "eggs",
    "lamb", "bacon", "ham", "salmon", "tuna", "duck", "meat", "sausage", "turkey", "anchovies"
}

# Define dairy ingredients
DAIRY_INGREDIENTS: Set[str] = {
    "milk", "cheese", "butter", "cream", "yogurt", "ghee", "paneer", "curd", "buttermilk",
    "whey", "casein", "lactose", "mozzarella", "parmesan", "cheddar", "ricotta", "brie"
}

# Define gluten-containing ingredients
GLUTEN_INGREDIENTS: Set[str] = {
    "wheat", "barley", "rye", "flour", "bread", "pasta", "noodles", "couscous", "semolina",
    "bulgur", "farina", "seitan", "soy sauce", "beer", "malt", "graham", "matzo"
}

# Define high-FODMAP ingredients
HIGH_FODMAP_INGREDIENTS: Set[str] = {
    "onion", "garlic", "apple", "pear", "watermelon", "honey", "wheat", "rye", "barley",
    "beans", "lentils", "chickpeas", "cashews", "pistachios", "milk", "ice cream", "yogurt",
    "cauliflower", "mushrooms", "artichoke"
}

# Define animal-derived ingredients (for vegan classification)
ANIMAL_DERIVED_INGREDIENTS: Set[str] = {
    "milk", "cheese", "butter", "cream", "yogurt", "ghee", "paneer", "curd", "buttermilk",
    "egg", "eggs", "honey", "gelatin", "whey", "casein", "lactose", "chicken", "mutton", 
    "beef", "pork", "fish", "shrimp", "prawns", "crab", "lamb", "bacon", "ham", "salmon", 
    "tuna", "duck", "meat", "sausage", "turkey", "anchovies"
}

def classify_diet(ingredients: List[str]) -> List[str]:
    """
    Classify a recipe based on dietary restrictions.
    
    Args:
        ingredients: List of ingredients in the recipe
        
    Returns:
        List of diet classifications
    """
    if not ingredients:
        return ["unknown"]
    
    diet_types = []
    ingredients_text = ' '.join([ing.lower() for ing in ingredients])
    
    # Vegetarian classification
    if not any(non_veg in ingredients_text for non_veg in NON_VEG_INGREDIENTS):
        diet_types.append("vegetarian")
    else:
        diet_types.append("non-vegetarian")
    
    # Vegan classification
    if not any(animal in ingredients_text for animal in ANIMAL_DERIVED_INGREDIENTS):
        diet_types.append("vegan")
    
    # Gluten-free classification
    if not any(gluten in ingredients_text for gluten in GLUTEN_INGREDIENTS):
        diet_types.append("gluten-free")
    
    # Dairy-free classification
    if not any(dairy in ingredients_text for dairy in DAIRY_INGREDIENTS):
        diet_types.append("dairy-free")
    
    # Low-FODMAP classification
    if not any(fodmap in ingredients_text for fodmap in HIGH_FODMAP_INGREDIENTS):
        diet_types.append("low-fodmap")
    
    return diet_types

def clean_ingredient_list(ingredients_str: str) -> List[str]:
    """
    Clean and parse ingredients string into a proper list.
    
    Args:
        ingredients_str: String containing ingredients
        
    Returns:
        List of cleaned ingredients
    """
    if not isinstance(ingredients_str, str):
        return []
    
    # Handle case where the string might already be in list-like format
    if ingredients_str.startswith('[') and ingredients_str.endswith(']'):
        # Remove the outer brackets and split by commas
        ingredients_str = ingredients_str[1:-1]
        # Split by comma but respect quotes
        ingredients = []
        for item in re.findall(r'\'([^\']*?)\'|"([^"]*?)"', ingredients_str):
            # Each item is a tuple with one empty value
            ingredient = item[0] if item[0] else item[1]
            if ingredient.strip():
                ingredients.append(ingredient.strip())
        return ingredients
    
    # Handle simple comma-separated list
    return [ing.strip() for ing in ingredients_str.split(',') if ing.strip()]

def extract_base_ingredient(ingredient: str) -> str:
    """
    Extract the base ingredient name without quantities, units, or preparation instructions.
    
    Args:
        ingredient: Full ingredient string (e.g., "1 tablespoon Red Chilli powder")
        
    Returns:
        Base ingredient name (e.g., "red chilli powder")
    """
    # Convert to lowercase first for easier pattern matching
    ingredient = ingredient.lower()
    
    # Remove quantity patterns (numbers at the beginning)
    ingredient = re.sub(r'^\d+(?:/\d+)?(?:\s*-\s*\d+(?:/\d+)?)?', '', ingredient)
    
    # Remove common units
    units = [
        'tablespoon', 'tbsp', 'teaspoon', 'tsp', 'cup', 'cups', 'ounce', 'oz', 
        'pound', 'lb', 'gram', 'g', 'kg', 'ml', 'liter', 'l', 'pinch', 'dash',
        'handful', 'bunch', 'can', 'cans', 'clove', 'cloves', 'piece', 'pieces'
    ]
    for unit in units:
        ingredient = re.sub(r'^\s*' + unit + r's?\s+', '', ingredient)
    
    # Remove preparation instructions (anything after a hyphen)
    if ' - ' in ingredient:
        ingredient = ingredient.split(' - ')[0]
    
    # Remove parenthetical text (often contains alternative names)
    ingredient = re.sub(r'\s*\([^)]*\)', '', ingredient)
    
    # Remove any remaining leading numbers
    ingredient = re.sub(r'^\s*\d+\s*', '', ingredient)
    
    # Strip whitespace and return
    return ingredient.strip()

def process_instructions(instructions_str: str) -> List[str]:
    """
    Process instructions string into a list of steps.
    
    Args:
        instructions_str: String containing recipe instructions
        
    Returns:
        List of instruction steps
    """
    if not isinstance(instructions_str, str):
        return []
    
    # Handle case where the string might already be in list-like format
    if instructions_str.startswith('[') and instructions_str.endswith(']'):
        # Remove the outer brackets
        instructions_str = instructions_str[1:-1]
        # Extract content within quotes
        instructions = []
        for item in re.findall(r'\'([^\']*?)\'|"([^"]*?)"', instructions_str):
            # Each item is a tuple with one empty value
            instruction = item[0] if item[0] else item[1]
            if instruction.strip():
                instructions.append(instruction.strip())
        
        # If we got a single string, split it into steps
        if len(instructions) == 1:
            return split_instruction_into_steps(instructions[0])
        return instructions
    
    return split_instruction_into_steps(instructions_str)

def split_instruction_into_steps(instruction: str) -> List[str]:
    """Split a single instruction string into multiple steps."""
    if not instruction:
        return []
    
    # Replace literal '\n' with actual newlines
    instruction = instruction.replace('\\n', '\n')
    
    # First split by newlines
    lines = []
    for line in instruction.split('\n'):
        line = line.strip()
        if line:
            lines.append(line)
    
    # Process each line to further split by sentence boundaries
    steps = []
    for line in lines:
        # Look for common sentence patterns
        # This regex splits on periods, exclamation marks, or question marks
        # followed by a space or end of string, and also on common conjunctions
        sentence_parts = re.split(r'(?<=[.!?])(?=\s|$)|(?<=\s)(?:Once|Then|Next|After|When)\s', line)
        
        # Also split on periods followed by capital letters (likely sentence boundaries)
        refined_parts = []
        for part in sentence_parts:
            subparts = re.split(r'(?<=\.)(?=[A-Z])', part)
            refined_parts.extend(subparts)
        
        for part in refined_parts:
            part = part.strip()
            if part:
                steps.append(part)
    
    return steps

def main() -> None:
    """Main function to import recipes into MongoDB."""
    try:
        # Load the cleaned dataset
        csv_path = "cleaned_recipeDataset.csv"
        logger.info(f"Loading dataset from {csv_path}")
        df = pd.read_csv(csv_path)
        
        # Connect to MongoDB
        mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
        logger.info(f"Connecting to MongoDB at {mongo_uri}")
        client = MongoClient(mongo_uri)
        db = client["recipeDB"]
        collection = db["recipes"]
        
        # Process data to match desired structure
        logger.info("Processing data to match desired structure")
        
        # Ensure column names match the desired structure
        if "Cuisine" not in df.columns and "cuisine" in df.columns:
            df.rename(columns={"cuisine": "Cuisine"}, inplace=True)
        
        # Process ingredients
        if "ingredients" in df.columns:
            # Clean and parse ingredients
            logger.info("Processing ingredients")
            df["ingredients"] = df["ingredients"].apply(clean_ingredient_list)
            
            # Create cleaned_ingredients as an array of base ingredient names
            logger.info("Creating cleaned_ingredients array")
            df["cleaned_ingredients"] = df["ingredients"].apply(
                lambda ingredients: [extract_base_ingredient(ing) for ing in ingredients]
            )
            
            # Add ingredient_count
            df["ingredient_count"] = df["ingredients"].apply(len)
        
        # Process instructions
        if "instructions" in df.columns:
            logger.info("Processing instructions into separate steps")
            df["instructions"] = df["instructions"].apply(process_instructions)
        
        # Classify diet - now returns a list of diet types
        logger.info("Classifying recipes by diet types")
        df["diet"] = df["ingredients"].apply(classify_diet)
        
        # Rename fields to use consistent naming convention
        logger.info("Standardizing field names")
        rename_map = {
            "Image-url": "image_url",
            "Ingredient-count": "ingredient_count"
        }
        df.rename(columns=rename_map, inplace=True)
        
        # Remove redundant Cleaned-Ingredients field if it exists
        if "Cleaned-Ingredients" in df.columns:
            logger.info("Removing redundant Cleaned-Ingredients field")
            df = df.drop(columns=["Cleaned-Ingredients"])
        
        # Convert DataFrame to dictionary format for MongoDB
        logger.info("Converting data to MongoDB format")
        data = df.to_dict(orient="records")
        
        # Drop existing collection to avoid duplicates
        logger.info("Dropping existing collection")
        collection.drop()
        
        # Insert new data
        logger.info(f"Inserting {len(data)} recipes into MongoDB")
        if data:
            # MongoDB will automatically create _id field
            collection.insert_many(data)
            
            # Create indexes for better query performance
            logger.info("Creating indexes")
            collection.create_index([("Cuisine", 1)])
            collection.create_index([("diet", 1)])
            collection.create_index([("RecipeName", 1)])
            collection.create_index([("cleaned_ingredients", 1)])
            
            logger.info("✅ Recipes successfully imported into MongoDB!")
        else:
            logger.error("No data to import!")
            
    except FileNotFoundError:
        logger.error(f"CSV file not found: {csv_path}")
    except Exception as e:
        logger.error(f"Error importing recipes: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()
