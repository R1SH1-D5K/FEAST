import logging
from typing import Dict, List, Any, Optional, Callable
import re
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RecipeFilter:
    """Advanced recipe filtering and sorting capabilities"""
    
    @staticmethod
    def filter_recipes(recipes: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Filter recipes based on multiple criteria"""
        if not recipes:
            return []
        
        if not filters:
            return recipes
        
        filtered_recipes = recipes.copy()
        
        # Apply each filter
        for filter_name, filter_value in filters.items():
            filter_method = getattr(RecipeFilter, f"filter_by_{filter_name}", None)
            
            if filter_method and callable(filter_method):
                filtered_recipes = filter_method(filtered_recipes, filter_value)
            else:
                logger.warning(f"Unknown filter: {filter_name}")
        
        return filtered_recipes
    
    @staticmethod
    def sort_recipes(recipes: List[Dict[str, Any]], sort_by: str, ascending: bool = True) -> List[Dict[str, Any]]:
        """Sort recipes by various criteria"""
        if not recipes:
            return []
        
        # Define sorting functions
        sort_functions = {
            "name": lambda r: r.get("RecipeName", "").lower(),
            "time": RecipeFilter._extract_time_minutes,
            "rating": lambda r: r.get("rating", 0),
            "calories": lambda r: r.get("nutrition", {}).get("calories", 1000),
            "protein": lambda r: r.get("nutrition", {}).get("protein", 0),
            "date_added": lambda r: datetime.fromisoformat(r.get("date_added", "2000-01-01T00:00:00"))
        }
        
        # Get sort function
        sort_func = sort_functions.get(sort_by)
        
        if not sort_func:
            logger.warning(f"Unknown sort criterion: {sort_by}, using name")
            sort_func = sort_functions["name"]
        
        # Sort recipes
        try:
            sorted_recipes = sorted(recipes, key=sort_func, reverse=not ascending)
            return sorted_recipes
        except Exception as e:
            logger.error(f"Error sorting recipes: {e}")
            return recipes
    
    @staticmethod
    def filter_by_diet(recipes: List[Dict[str, Any]], diet: str) -> List[Dict[str, Any]]:
        """Filter recipes by diet type"""
        if not diet:
            return recipes
        
        diet = diet.lower()
        return [r for r in recipes if r.get("diet", "").lower() == diet]
    
    @staticmethod
    def filter_by_cuisine(recipes: List[Dict[str, Any]], cuisine: str) -> List[Dict[str, Any]]:
        """Filter recipes by cuisine"""
        if not cuisine:
            return recipes
        
        cuisine = cuisine.lower()
        return [r for r in recipes if r.get("Cuisine", "").lower() == cuisine]
    
    @staticmethod
    def filter_by_ingredient(recipes: List[Dict[str, Any]], ingredient: str) -> List[Dict[str, Any]]:
        """Filter recipes that contain a specific ingredient"""
        if not ingredient:
            return recipes
        
        ingredient = ingredient.lower()
        return [r for r in recipes if any(ingredient in ing.lower() for ing in r.get("ingredients", []))]
    
    @staticmethod
    def filter_by_exclude_ingredient(recipes: List[Dict[str, Any]], ingredient: str) -> List[Dict[str, Any]]:
        """Filter recipes that do NOT contain a specific ingredient"""
        if not ingredient:
            return recipes
        
        ingredient = ingredient.lower()
        return [r for r in recipes if not any(ingredient in ing.lower() for ing in r.get("ingredients", []))]
    
    @staticmethod
    def filter_by_max_time(recipes: List[Dict[str, Any]], max_minutes: int) -> List[Dict[str, Any]]:
        """Filter recipes that can be prepared within a maximum time"""
        if not max_minutes:
            return recipes
        
        return [r for r in recipes if RecipeFilter._extract_time_minutes(r) <= max_minutes]
    
    @staticmethod
    def filter_by_max_calories(recipes: List[Dict[str, Any]], max_calories: int) -> List[Dict[str, Any]]:
        """Filter recipes with calories under a threshold"""
        if not max_calories:
            return recipes
        
        return [r for r in recipes if r.get("nutrition", {}).get("calories", 1000) <= max_calories]
    
    @staticmethod
    def filter_by_min_protein(recipes: List[Dict[str, Any]], min_protein: int) -> List[Dict[str, Any]]:
        """Filter recipes with protein above a threshold"""
        if not min_protein:
            return recipes
        
        return [r for r in recipes if r.get("nutrition", {}).get("protein", 0) >= min_protein]
    
    @staticmethod
    def filter_by_course(recipes: List[Dict[str, Any]], course: str) -> List[Dict[str, Any]]:
        """Filter recipes by course type"""
        if not course:
            return recipes
        
        course = course.lower()
        return [r for r in recipes if r.get("course", "").lower() == course]
    
    @staticmethod
    def filter_by_taste(recipes: List[Dict[str, Any]], taste: str) -> List[Dict[str, Any]]:
        """Filter recipes by taste profile"""
        if not taste:
            return recipes
        
        taste = taste.lower()
        return [r for r in recipes if taste in r.get("taste", "").lower()]
    
    @staticmethod
    def filter_by_rating(recipes: List[Dict[str, Any]], min_rating: float) -> List[Dict[str, Any]]:
        """Filter recipes by minimum rating"""
        if not min_rating:
            return recipes
        
        return [r for r in recipes if r.get("rating", 0) >= min_rating]
    
    @staticmethod
    def _extract_time_minutes(recipe: Dict[str, Any]) -> int:
        """Extract cooking time in minutes from recipe"""
        time_str = recipe.get("time", "")
        if not time_str:
            return 60  # Default to 60 minutes
        
        # Try to extract minutes
        minutes_match = re.search(r'(\d+)\s*min', time_str.lower())
        if minutes_match:
            return int(minutes_match.group(1))
        
        # Try to extract hours and convert to minutes
        hours_match = re.search(r'(\d+)\s*hour', time_str.lower())
        if hours_match:
            return int(hours_match.group(1)) * 60
        
        # If no match, return default
        return 60

# Create a filter instance
recipe_filter = RecipeFilter() 