import logging
from pymongo import MongoClient
import os
import json
import random
import re

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MongoDB connection
try:
    mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
    client = MongoClient(mongo_uri)
    db = client["recipeDB"]  # Your database name
    collection = db["recipes"]  # Your collection name
    logger.info("Connected to MongoDB")
    
    # Create indexes for better performance
    collection.create_index([("RecipeName", "text"), ("ingredients", "text")])
    collection.create_index([("Cuisine", 1)])
    collection.create_index([("diet", 1)])
    logger.info("Created MongoDB indexes for better performance")
    
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
    # Fallback to local recipes
    collection = None

# Sample recipes for fallback
SAMPLE_RECIPES = [
    # (Same recipes as in the ActionSearchRecipes class)
]

# Add to recipe_db.py - Ingredient-based search and substitutions

INGREDIENT_SUBSTITUTIONS = {
    "bell pepper": ["capsicum", "sweet pepper"],
    "cilantro": ["coriander", "chinese parsley"],
    "eggplant": ["aubergine"],
    "zucchini": ["courgette"],
    "scallion": ["green onion", "spring onion"],
    "arugula": ["rocket"],
    "chickpeas": ["garbanzo beans"],
    "ground beef": ["minced beef", "hamburger meat"],
    "powdered sugar": ["icing sugar", "confectioners' sugar"],
    "heavy cream": ["double cream", "whipping cream"],
    "all-purpose flour": ["plain flour"],
    "cornstarch": ["corn flour"],
    "baking soda": ["bicarbonate of soda"],
    "cookie": ["biscuit"],
    "shrimp": ["prawns"],
    "candy": ["sweets"],
    "chips": ["crisps"],
    "french fries": ["chips"],
    "ketchup": ["tomato sauce"],
    "jelly": ["jam"]
}

# Add nutritional filtering capabilities
NUTRITIONAL_KEYWORDS = {
    "low-calorie": {"calories": {"$lt": 400}},
    "low-carb": {"carbohydrates": {"$lt": 20}},
    "high-protein": {"protein": {"$gt": 20}},
    "low-fat": {"fat": {"$lt": 10}},
    "keto": {"carbohydrates": {"$lt": 10}, "fat": {"$gt": 20}},
    "balanced": {"protein": {"$gt": 15}, "carbohydrates": {"$gt": 30}, "fat": {"$gt": 10, "$lt": 30}}
}

def initialize_db():
    """Initialize the database with sample recipes if empty or if MongoDB is unreachable"""
    global collection
    
    try:
        if collection and collection.count_documents({}) == 0:
            logger.info("Initializing database with sample recipes")
            # Insert sample recipes
            collection.insert_many(SAMPLE_RECIPES)
            logger.info(f"Inserted {len(SAMPLE_RECIPES)} sample recipes")
            
            # Create indexes for better performance
            collection.create_index([("RecipeName", "text"), ("ingredients", "text")])
            collection.create_index([("Cuisine", 1)])
            collection.create_index([("diet", 1)])
            collection.create_index([("course", 1)])
            collection.create_index([("time", 1)])
            logger.info("Created MongoDB indexes for better performance")
    except Exception as e:
        logger.error(f"Error initializing MongoDB: {e}")
        logger.info("Falling back to local sample recipes")
        collection = None  # Force use of local recipes

def build_optimized_query(preferences):
    """Build an optimized MongoDB query based on user preferences"""
    query = {}
    
    # Add diet filter with proper indexing
    if preferences.get("diet"):
        diet = preferences["diet"].lower()
        query["diet"] = {"$regex": diet, "$options": "i"}
    
    # Add cuisine filter
    if preferences.get("cuisine"):
        query["Cuisine"] = {"$regex": preferences["cuisine"], "$options": "i"}
    
    # Add course filter (look in recipe name or description)
    if preferences.get("course"):
        course_regex = preferences["course"]
        query["$or"] = [
            {"RecipeName": {"$regex": course_regex, "$options": "i"}},
            {"Description": {"$regex": course_regex, "$options": "i"}}
        ]
    
    # Add ingredient filter
    if preferences.get("ingredient"):
        # If we already have $or for course, we need to handle differently
        if "$or" in query:
            # Save the existing $or
            existing_or = query["$or"]
            # Create a new $and that combines the existing $or with the ingredient condition
            query = {
                "$and": [
                    {"$or": existing_or},
                    {"ingredients": {"$regex": preferences["ingredient"], "$options": "i"}}
                ]
            }
        else:
            query["ingredients"] = {"$regex": preferences["ingredient"], "$options": "i"}
    
    # Handle exclusions separately
    if preferences.get("exclude_ingredient"):
        exclude_regex = preferences["exclude_ingredient"]
        # If we already have a complex query, add to $and
        if "$and" in query:
            query["$and"].append({"ingredients": {"$not": {"$regex": exclude_regex, "$options": "i"}}})
        else:
            # If we have $or but no $and
            if "$or" in query:
                # Save the existing $or
                existing_or = query["$or"]
                # Create a new $and that combines the existing $or with the exclusion
                query = {
                    "$and": [
                        {"$or": existing_or},
                        {"ingredients": {"$not": {"$regex": exclude_regex, "$options": "i"}}}
                    ]
                }
                # Remove the original $or
                del query["$or"]
            else:
                # Simple case - just add the exclusion
                query["ingredients"] = {"$not": {"$regex": exclude_regex, "$options": "i"}}
    
    # Handle time constraints
    if preferences.get("time"):
        time_value = preferences["time"].lower()
        if "quick" in time_value or "fast" in time_value or "easy" in time_value:
            # For quick recipes, look for TotalTimeInMins < 30
            if "$and" in query:
                query["$and"].append({"TotalTimeInMins": {"$lt": 30}})
            else:
                query["TotalTimeInMins"] = {"$lt": 30}
        elif "under" in time_value or "less than" in time_value:
            # Extract the number of minutes
            time_match = re.search(r"(\d+)", time_value)
            if time_match:
                minutes = int(time_match.group(1))
                if "$and" in query:
                    query["$and"].append({"TotalTimeInMins": {"$lt": minutes}})
                else:
                    query["TotalTimeInMins"] = {"$lt": minutes}
    
    return query

def search_with_fallback(preferences, max_relaxations=3):
    """Search for recipes with intelligent fallback mechanisms"""
    try:
        if not collection:
            # MongoDB unavailable, use local filtering
            logger.warning("MongoDB unavailable, using local recipe filtering")
            results = filter_recipes(SAMPLE_RECIPES, preferences)
            if results:
                return {"results": results, "relaxed": []}
            else:
                # Try relaxing constraints one by one
                relaxed = []
                relaxed_preferences = preferences.copy()
                
                # Priority of constraints to relax
                relaxation_order = ["time", "taste", "exclude_ingredient", "ingredient", "course", "cuisine", "diet"]
                
                for constraint in relaxation_order:
                    if constraint in relaxed_preferences:
                        del relaxed_preferences[constraint]
                        relaxed.append(constraint)
                        
                        results = filter_recipes(SAMPLE_RECIPES, relaxed_preferences)
                        if results:
                            return {"results": results, "relaxed": relaxed}
                        
                        # Stop after max_relaxations
                        if len(relaxed) >= max_relaxations:
                            break
                
                # If still no results, return any recipes
                return {"results": SAMPLE_RECIPES[:5], "relaxed": list(preferences.keys())}
        
        # Try exact match first
        query = build_optimized_query(preferences)
        results = list(collection.find(query).limit(10))
        
        if results:
            return {"results": results, "relaxed": []}
        
        # If no results, try relaxing constraints one by one
        relaxed = []
        relaxed_preferences = preferences.copy()
        
        # Priority of constraints to relax
        relaxation_order = ["time", "taste", "exclude_ingredient", "ingredient", "course", "cuisine", "diet"]
        
        for constraint in relaxation_order:
            if constraint in relaxed_preferences:
                del relaxed_preferences[constraint]
                relaxed.append(constraint)
                
                query = build_optimized_query(relaxed_preferences)
                results = list(collection.find(query).limit(10))
                
                if results:
                    return {"results": results, "relaxed": relaxed}
                
                # Stop after max_relaxations
                if len(relaxed) >= max_relaxations:
                    break
        
        # If still no results, try minimal constraints
        if "diet" in preferences:
            minimal_preferences = {"diet": preferences["diet"]}
            query = build_optimized_query(minimal_preferences)
            results = list(collection.find(query).limit(10))
            if results:
                for k in preferences.keys():
                    if k != "diet" and k not in relaxed:
                        relaxed.append(k)
                return {"results": results, "relaxed": relaxed}
        
        # Absolute last resort: return any recipes
        results = list(collection.find({}).limit(10))
        return {"results": results, "relaxed": list(preferences.keys())}
        
    except Exception as e:
        logger.error(f"Error in search_with_fallback: {e}")
        # Fall back to local filtering in case of any error
        logger.warning("Error occurred, falling back to local recipe filtering")
        results = filter_recipes(SAMPLE_RECIPES, preferences)
        if results:
            return {"results": results, "relaxed": []}
        else:
            # Return any sample recipes as a last resort
            return {"results": SAMPLE_RECIPES[:5], "relaxed": list(preferences.keys())}

def filter_recipes(recipes, preferences):
    """Filter recipes based on preferences (fallback method)"""
    filtered_recipes = []
    for recipe in recipes:
        match = True
        
        if preferences.get("diet") and preferences["diet"].lower() != recipe.get("diet", "").lower():
            if preferences["diet"].lower() == "vegetarian" and recipe.get("diet") == "non-vegetarian":
                match = False
        
        if preferences.get("cuisine") and preferences["cuisine"].lower() not in recipe.get("cuisine", "").lower():
            match = False
        
        if preferences.get("course") and preferences["course"].lower() not in recipe.get("course", "").lower():
            match = False
        
        if preferences.get("ingredient"):
            ingredient_found = False
            for recipe_ingredient in recipe.get("ingredients", []):
                if preferences["ingredient"].lower() in recipe_ingredient.lower():
                    ingredient_found = True
                    break
            if not ingredient_found:
                match = False
        
        if preferences.get("exclude_ingredient"):
            for recipe_ingredient in recipe.get("ingredients", []):
                if preferences["exclude_ingredient"].lower() in recipe_ingredient.lower():
                    match = False
                    break
        
        if preferences.get("time") and "quick" in preferences["time"].lower():
            recipe_time = recipe.get("time", "")
            if "hour" in recipe_time.lower() or int(recipe_time.split()[0]) > 30:
                match = False
        
        if match:
            filtered_recipes.append(recipe)
    
    return filtered_recipes

def format_recipe(recipe):
    """Format a recipe for display"""
    recipe_text = f"""
**{recipe['name']}**
**Cuisine:** {recipe['cuisine']}
**Course:** {recipe['course']}
**Time:** {recipe['time']}
**Diet:** {recipe['diet']}

**Ingredients:**
{chr(10).join(['• ' + ingredient for ingredient in recipe['ingredients']])}

**Instructions:**
{chr(10).join([f"{i+1}. {step}" for i, step in enumerate(recipe['instructions'])])}
"""
    return recipe_text

def search_by_available_ingredients(available_ingredients, min_match_percentage=0.6):
    """Search for recipes based on ingredients the user has available"""
    if not collection:
        return filter_by_available_ingredients(SAMPLE_RECIPES, available_ingredients, min_match_percentage)
    
    try:
        # Convert ingredients to lowercase for case-insensitive matching
        normalized_ingredients = [ing.lower().strip() for ing in available_ingredients]
        
        # Find recipes that contain at least some of these ingredients
        ingredient_query = {"ingredients": {"$in": normalized_ingredients}}
        potential_recipes = list(collection.find(ingredient_query))
        
        # Rank recipes by percentage of matching ingredients
        ranked_recipes = []
        for recipe in potential_recipes:
            recipe_ingredients = [ing.lower() for ing in recipe.get('ingredients', [])]
            
            # Count matching ingredients
            matching_count = sum(1 for ing in recipe_ingredients if any(
                available_ing in ing or ing in available_ing 
                for available_ing in normalized_ingredients
            ))
            
            # Calculate match percentage
            match_percentage = matching_count / len(recipe_ingredients) if recipe_ingredients else 0
            
            # Only include recipes that meet the minimum match percentage
            if match_percentage >= min_match_percentage:
                ranked_recipes.append({
                    "recipe": recipe,
                    "match_percentage": match_percentage,
                    "missing_ingredients": len(recipe_ingredients) - matching_count
                })
        
        # Sort by match percentage (highest first)
        ranked_recipes.sort(key=lambda x: x["match_percentage"], reverse=True)
        
        return [item["recipe"] for item in ranked_recipes]
    
    except Exception as e:
        logger.error(f"Error searching by available ingredients: {e}")
        return []

def filter_by_available_ingredients(recipes, available_ingredients, min_match_percentage=0.6):
    """Filter and rank recipes by available ingredients (local fallback)"""
    normalized_ingredients = [ing.lower().strip() for ing in available_ingredients]
    
    ranked_recipes = []
    for recipe in recipes:
        recipe_ingredients = [ing.lower() for ing in recipe.get('ingredients', [])]
        
        # Count matching ingredients
        matching_count = sum(1 for ing in recipe_ingredients if any(
            available_ing in ing or ing in available_ing 
            for available_ing in normalized_ingredients
        ))
        
        # Calculate match percentage
        match_percentage = matching_count / len(recipe_ingredients) if recipe_ingredients else 0
        
        # Only include recipes that meet the minimum match percentage
        if match_percentage >= min_match_percentage:
            ranked_recipes.append({
                "recipe": recipe,
                "match_percentage": match_percentage,
                "missing_ingredients": len(recipe_ingredients) - matching_count
            })
    
    # Sort by match percentage (highest first)
    ranked_recipes.sort(key=lambda x: x["match_percentage"], reverse=True)
    
    return [item["recipe"] for item in ranked_recipes]

def suggest_ingredient_substitutions(recipe):
    """Suggest substitutions for ingredients in a recipe"""
    suggestions = []
    
    for ingredient in recipe.get('ingredients', []):
        ingredient_lower = ingredient.lower()
        
        for main_ingredient, substitutes in INGREDIENT_SUBSTITUTIONS.items():
            if main_ingredient in ingredient_lower:
                suggestions.append({
                    "original": ingredient,
                    "substitutes": substitutes
                })
                break
                
            # Check if any substitute matches and suggest the main ingredient
            for substitute in substitutes:
                if substitute in ingredient_lower:
                    suggestions.append({
                        "original": ingredient,
                        "substitutes": [main_ingredient]
                    })
                    break
    
    return suggestions

def format_recipe_with_substitutions(recipe):
    """Format a recipe with ingredient substitution suggestions"""
    recipe_text = format_recipe(recipe)
    
    # Get substitution suggestions
    substitutions = suggest_ingredient_substitutions(recipe)
    
    if substitutions:
        recipe_text += "\n\n**Ingredient Substitutions:**"
        for sub in substitutions:
            recipe_text += f"\n• Instead of {sub['original']}, you could use: {', '.join(sub['substitutes'])}"
    
    return recipe_text

def search_with_weighted_scoring(preferences, weights=None):
    """Search for recipes with weighted scoring based on user preferences"""
    # Default weights if none provided
    if weights is None:
        weights = {
            "diet": 10.0,        # Highest priority - dietary restrictions
            "exclude_ingredient": 8.0,  # High priority - excluded ingredients
            "cuisine": 5.0,      # Medium priority
            "course": 4.0,       # Medium priority
            "time": 3.0,         # Lower priority
            "ingredient": 2.0,   # Lower priority
            "taste": 1.0         # Lowest priority
        }
    
    try:
        # Get all potential recipes
        if not collection:
            all_recipes = SAMPLE_RECIPES
        else:
            # Use a minimal query to get potential matches
            minimal_query = {}
            
            # Only add diet as a hard filter
            if "diet" in preferences:
                minimal_query["diet"] = {"$regex": preferences["diet"], "$options": "i"}
            
            # Only add exclude_ingredient as a hard filter
            if "exclude_ingredient" in preferences:
                exclude_ingredient = preferences["exclude_ingredient"]
                minimal_query["ingredients"] = {"$not": {"$regex": exclude_ingredient, "$options": "i"}}
            
            all_recipes = list(collection.find(minimal_query))
        
        # Score each recipe
        scored_recipes = []
        for recipe in all_recipes:
            score = 0.0
            matches = {}
            
            # Calculate score based on each preference
            for pref, weight in weights.items():
                if pref not in preferences:
                    continue
                
                value = preferences[pref]
                
                # Different scoring logic based on preference type
                if pref == "diet":
                    if "diet" in recipe and value.lower() in recipe["diet"].lower():
                        score += weight
                        matches[pref] = True
                
                elif pref == "exclude_ingredient":
                    # Check if excluded ingredient is not in recipe
                    excluded = False
                    for ingredient in recipe.get("ingredients", []):
                        if value.lower() in ingredient.lower():
                            excluded = True
                            break
                    
                    if not excluded:
                        score += weight
                        matches[pref] = True
                
                elif pref == "cuisine":
                    if "Cuisine" in recipe and value.lower() in recipe["Cuisine"].lower():
                        score += weight
                        matches[pref] = True
                
                elif pref == "course":
                    # Check in name or description
                    if (("RecipeName" in recipe and value.lower() in recipe["RecipeName"].lower()) or
                        ("Description" in recipe and value.lower() in recipe["Description"].lower())):
                        score += weight
                        matches[pref] = True
                
                elif pref == "time":
                    # Check if recipe mentions quick or time constraints
                    if ("time" in recipe and value.lower() in recipe["time"].lower()) or \
                       ("RecipeName" in recipe and "quick" in recipe["RecipeName"].lower()) or \
                       ("Description" in recipe and "quick" in recipe["Description"].lower()):
                        score += weight
                        matches[pref] = True
                
                elif pref == "ingredient":
                    # Check if ingredient is in recipe
                    for ingredient in recipe.get("ingredients", []):
                        if value.lower() in ingredient.lower():
                            score += weight
                            matches[pref] = True
                            break
                
                elif pref == "taste":
                    # Check if taste is mentioned in name or description
                    if (("RecipeName" in recipe and value.lower() in recipe["RecipeName"].lower()) or
                        ("Description" in recipe and value.lower() in recipe["Description"].lower()) or
                        ("taste" in recipe and value.lower() in recipe["taste"].lower())):
                        score += weight
                        matches[pref] = True
            
            # Add recipe with its score
            scored_recipes.append({
                "recipe": recipe,
                "score": score,
                "matches": matches,
                "match_percentage": sum(1 for m in matches.values() if m) / len(preferences) if preferences else 0
            })
        
        # Sort by score (highest first)
        scored_recipes.sort(key=lambda x: x["score"], reverse=True)
        
        # Return top results with score information
        return {
            "results": [item["recipe"] for item in scored_recipes[:10]],
            "detailed_results": scored_recipes[:10],
            "total_matches": len(scored_recipes),
            "relaxed": []  # No relaxation needed with scoring approach
        }
    
    except Exception as e:
        logger.error(f"Error in search_with_weighted_scoring: {e}")
        # Fall back to basic search
        return search_with_fallback(preferences)

def extract_nutritional_preferences(text):
    """Extract nutritional preferences from text"""
    preferences = {}
    
    text_lower = text.lower()
    
    for keyword, query in NUTRITIONAL_KEYWORDS.items():
        if keyword in text_lower:
            preferences.update(query)
    
    # Handle specific numeric values
    calorie_match = re.search(r'under (\d+) calories', text_lower)
    if calorie_match:
        preferences["calories"] = {"$lt": int(calorie_match.group(1))}
    
    protein_match = re.search(r'at least (\d+)g? of protein', text_lower)
    if protein_match:
        preferences["protein"] = {"$gt": int(protein_match.group(1))}
    
    return preferences

# Add database optimization functions
def create_optimized_indexes():
    """Create optimized indexes for better performance"""
    if not collection:
        logger.warning("MongoDB not available, skipping index creation")
        return
    
    try:
        # Text index for full-text search
        collection.create_index([
            ("RecipeName", "text"), 
            ("Description", "text"),
            ("ingredients", "text")
        ])
        
        # Single field indexes for common queries
        collection.create_index([("Cuisine", 1)])
        collection.create_index([("diet", 1)])
        collection.create_index([("course", 1)])
        collection.create_index([("time", 1)])
        
        # Compound indexes for common combinations
        collection.create_index([("diet", 1), ("Cuisine", 1)])
        collection.create_index([("diet", 1), ("course", 1)])
        
        logger.info("Created optimized MongoDB indexes")
    except Exception as e:
        logger.error(f"Error creating indexes: {e}")

# Call this function during initialization
create_optimized_indexes()

# Initialize the database when the module is imported
if collection:
    initialize_db() 