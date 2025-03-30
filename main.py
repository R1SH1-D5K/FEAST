from fastapi import FastAPI, HTTPException, Query
from pymongo import MongoClient
import json
import math
import os
import logging
from typing import Optional, List
from rasa_sdk.executor import ActionExecutor

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import actions directly from the file
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from actions import ActionGetRecipes, ActionClearPreferences

app = FastAPI(
    title="Recipe Chatbot API",
    description="API for retrieving and filtering recipes",
    version="1.0.0",
    docs_url="/docs",  # Explicitly enable docs
    redoc_url="/redoc"  # Explicitly enable ReDoc
)

# Connect to MongoDB using environment variable or default to localhost
mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(mongo_uri)
db = client["recipeDB"]
collection = db["recipes"]

# Ensure indexes exist
collection.create_index([("Cuisine", 1)])
collection.create_index([("diet", 1)])
collection.create_index([("RecipeName", 1)])
# Add text index for search functionality
collection.create_index([("RecipeName", "text"), ("ingredients", "text")])

logger.info("Indexes created on Cuisine, diet, RecipeName, and text search fields.")

# Create an executor
executor = ActionExecutor()

# Register your actions
executor.register_action(ActionGetRecipes())
executor.register_action(ActionClearPreferences())

# Run the executor
if __name__ == "__main__":
    executor.run(port=5055)

@app.get("/recipes", 
         summary="Get recipes with pagination and filters",
         description="Retrieve recipes with optional filtering by cuisine and diet types")
def get_recipes(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=50, description="Number of recipes per page"),
    cuisine: Optional[str] = Query(None, description="Filter by cuisine type"),
    diet: Optional[str] = Query(None, description="Comma-separated list of diet filters (vegetarian, non-vegetarian, vegan, gluten-free, dairy-free, low-fodmap)"),
    diet_mode: str = Query("and", regex="^(and|or)$", description="Filter mode: 'and' (default) requires all diets, 'or' allows any")
):
    try:
        logger.info(f"Fetching recipes - Page: {page}, Limit: {limit}, Cuisine: {cuisine}, Diet: {diet}, Diet Mode: {diet_mode}")

        # Validate input parameters
        if cuisine and not cuisine.strip():
            raise HTTPException(status_code=400, detail="Cuisine parameter cannot be empty")
        if diet and not diet.strip():
            raise HTTPException(status_code=400, detail="Diet parameter cannot be empty")

        skip = (page - 1) * limit
        query = {}

        # Use broader regex match for cuisine
        if cuisine:
            query["Cuisine"] = {"$regex": cuisine, "$options": "i"}  
        
        # Handle multiple diet filters with AND/OR logic
        if diet:
            diet_filters = [d.strip().lower() for d in diet.split(",") if d.strip()]
            if diet_filters:
                if diet_mode.lower() == "and":
                    query["diet"] = {"$all": diet_filters}  # Recipe must have ALL diets
                else:
                    query["diet"] = {"$in": diet_filters}   # Recipe must have AT LEAST ONE diet

        total_recipes = collection.count_documents(query)
        total_pages = math.ceil(total_recipes / limit) if total_recipes > 0 else 0
        
        logger.info(f"MongoDB Query: {query}, Total Recipes: {total_recipes}, Total Pages: {total_pages}")

        # Validate page number against total pages
        if total_recipes > 0 and page > total_pages:
            raise HTTPException(status_code=400, detail=f"Page number exceeds total pages ({total_pages})")

        recipes = list(collection.find(query, {"_id": 0}).skip(skip).limit(limit))

        formatted_recipes = []
        for recipe in recipes:
            formatted_recipes.append({
                "name": recipe.get("RecipeName"),
                "ingredients": recipe.get("ingredients", ["Ingredients not available"]),
                "instructions": recipe.get("instructions", ["Instructions not available"]),
                "cuisine": recipe.get("Cuisine", "Unknown"),
                "diet": recipe.get("diet", "Unknown"),
                "total_time_mins": recipe.get("TotalTimeInMins", "Unknown"),
                "image_url": recipe.get("image_url", recipe.get("Image-url", "N/A")),
                "source_link": recipe.get("URL", "N/A"),
            })

        if not formatted_recipes:
            raise HTTPException(status_code=404, detail="No recipes found.")

        return {
            "metadata": {
                "page": page,
                "limit": limit,
                "total_recipes": total_recipes,
                "total_pages": total_pages,
                "has_next": page * limit < total_recipes,
                "has_previous": page > 1,
            },
            "recipes": formatted_recipes,
        }
    except Exception as e:
        logger.error(f"Error in get_recipes: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error occurred")


@app.get("/", summary="Home endpoint", description="Returns a welcome message")
def home():
    return {"message": "Recipe Chatbot API is running!"}


@app.get("/health", summary="Health check", description="Checks if the API and database connection are healthy")
def health_check():
    try:
        # Check if database is connected
        client.admin.command('ping')
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Database connection failed")


@app.get("/cuisines", summary="Get available cuisines", description="Returns a list of all available cuisines")
def get_cuisines():
    try:
        cuisines = collection.distinct("Cuisine")
        # Filter out None values and empty strings
        cuisines = [c for c in cuisines if c]
        return {"cuisines": sorted(cuisines)}
    except Exception as e:
        logger.error(f"Error fetching cuisines: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch cuisines")


@app.get("/diets", summary="Get available diets", description="Returns a list of all available diet types")
def get_diets():
    try:
        diets = collection.distinct("diet")
        # Filter out None values and empty strings
        diets = [d for d in diets if d]
        return {"diets": sorted(diets)}
    except Exception as e:
        logger.error(f"Error fetching diets: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch diets")


@app.get("/recipes/filter", 
         summary="Filter recipes by diet and exclude ingredients",
         description="Filter recipes by diet type (vegetarian, vegan, etc.) and exclude specific ingredients")
def get_filtered_recipes(
    diet: Optional[str] = Query(None, description="Comma-separated list of diets (vegetarian, vegan, gluten-free, etc.)"),
    diet_mode: str = Query("and", regex="^(and|or)$", description="Filter mode: 'and' (default) requires all diets, 'or' allows any"),
    exclude_ingredients: Optional[List[str]] = Query(None, description="List of ingredients to exclude"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=50, description="Number of recipes per page")
):
    try:
        logger.info(f"Filtering recipes - Diet: {diet}, Mode: {diet_mode}, Exclude: {exclude_ingredients}, Page: {page}, Limit: {limit}")
        
        query = {}

        # Handle diet filtering with AND/OR logic
        if diet:
            diet_filters = [d.strip().lower() for d in diet.split(",") if d.strip()]
            if diet_filters:
                if diet_mode.lower() == "and":
                    query["diet"] = {"$all": diet_filters}  # Recipe must have ALL diets
                else:
                    query["diet"] = {"$in": diet_filters}   # Recipe must have AT LEAST ONE diet

        # Handle exclude ingredients
        if exclude_ingredients:
            exclude_ingredients = [i.strip().lower() for i in exclude_ingredients if i.strip()]
            if exclude_ingredients:
                # Use cleaned_ingredients for more accurate exclusion if available
                if collection.find_one({"cleaned_ingredients": {"$exists": True}}):
                    query["cleaned_ingredients"] = {"$nin": exclude_ingredients}
                else:
                    # Fall back to ingredients field
                    # This is a more complex query that checks if any ingredient contains the excluded terms
                    exclude_conditions = []
                    for ingredient in exclude_ingredients:
                        exclude_conditions.append({"ingredients": {"$not": {"$regex": ingredient, "$options": "i"}}})
                    if exclude_conditions:
                        query["$and"] = exclude_conditions

        # Pagination logic
        total_recipes = collection.count_documents(query)
        total_pages = (total_recipes // limit) + (1 if total_recipes % limit else 0)
        
        logger.info(f"MongoDB Query: {query}, Total Recipes: {total_recipes}, Total Pages: {total_pages}")
        
        recipes = list(collection.find(query, {"_id": 0}).skip((page - 1) * limit).limit(limit))

        formatted_recipes = [
            {
                "name": recipe.get("RecipeName"),
                "ingredients": recipe.get("ingredients", ["Ingredients not available"]),
                "instructions": recipe.get("instructions", ["Instructions not available"]),
                "cuisine": recipe.get("Cuisine", "Unknown"),
                "diet": recipe.get("diet", "Unknown"),
                "total_time_mins": recipe.get("TotalTimeInMins", "Unknown"),
                "image_url": recipe.get("image_url", recipe.get("Image-url", "N/A")),
                "source_link": recipe.get("URL", "N/A"),
            }
            for recipe in recipes
        ]

        if not formatted_recipes:
            raise HTTPException(status_code=404, detail="No recipes found.")

        return {
            "metadata": {
                "page": page,
                "limit": limit,
                "total_recipes": total_recipes,
                "total_pages": total_pages,
                "has_next": page * limit < total_recipes,
                "has_previous": page > 1,
            },
            "recipes": formatted_recipes,
        }
        
    except Exception as e:
        logger.error(f"Error in get_filtered_recipes: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error occurred")
