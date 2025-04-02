import logging
from typing import Dict, List, Any, Optional, Tuple
import json
import os

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RecipeSubstitutionEngine:
    """Engine for suggesting ingredient substitutions in recipes"""
    
    def __init__(self):
        self.substitutions = {}
        self.dietary_substitutions = {}
        self.load_substitution_data()
    
    def load_substitution_data(self):
        """Load substitution data from files"""
        try:
            # Load general substitutions
            if os.path.exists("data/substitutions.json"):
                with open("data/substitutions.json", "r") as f:
                    self.substitutions = json.load(f)
                logger.info(f"Loaded {len(self.substitutions)} ingredient substitutions")
            
            # Load dietary substitutions
            if os.path.exists("data/dietary_substitutions.json"):
                with open("data/dietary_substitutions.json", "r") as f:
                    self.dietary_substitutions = json.load(f)
                logger.info(f"Loaded dietary substitutions for {len(self.dietary_substitutions)} diets")
        except Exception as e:
            logger.error(f"Error loading substitution data: {e}")
    
    def find_substitutions(self, ingredient: str) -> List[Dict[str, Any]]:
        """Find substitutions for a specific ingredient"""
        if not ingredient or not self.substitutions:
            return []
        
        ingredient = ingredient.lower()
        
        # Direct match
        if ingredient in self.substitutions:
            return self.substitutions[ingredient]
        
        # Partial match
        matches = []
        for key in self.substitutions:
            if key in ingredient or ingredient in key:
                matches.extend(self.substitutions[key])
        
        return matches
    
    def find_dietary_substitutions(self, ingredient: str, diet: str) -> List[Dict[str, Any]]:
        """Find substitutions for a specific ingredient based on dietary restrictions"""
        if not ingredient or not diet or not self.dietary_substitutions:
            return []
        
        ingredient = ingredient.lower()
        diet = diet.lower()
        
        # Check if we have substitutions for this diet
        if diet not in self.dietary_substitutions:
            return []
        
        diet_subs = self.dietary_substitutions[diet]
        
        # Direct match
        if ingredient in diet_subs:
            return diet_subs[ingredient]
        
        # Partial match
        matches = []
        for key in diet_subs:
            if key in ingredient or ingredient in key:
                matches.extend(diet_subs[key])
        
        return matches
    
    def suggest_recipe_substitutions(self, recipe: Dict[str, Any], diet: Optional[str] = None) -> List[Dict[str, Any]]:
        """Suggest substitutions for ingredients in a recipe"""
        if not recipe:
            return []
        
        ingredients = recipe.get("ingredients", [])
        if not ingredients:
            return []
        
        suggestions = []
        
        for ingredient in ingredients:
            # Find substitutions
            subs = []
            
            # If diet is specified, try dietary substitutions first
            if diet:
                subs = self.find_dietary_substitutions(ingredient, diet)
            
            # If no dietary substitutions found, try general substitutions
            if not subs:
                subs = self.find_substitutions(ingredient)
            
            if subs:
                suggestions.append({
                    "original": ingredient,
                    "substitutions": subs
                })
        
        return suggestions
    
    def format_substitution_suggestions(self, suggestions: List[Dict[str, Any]]) -> str:
        """Format substitution suggestions as human-readable text"""
        if not suggestions:
            return ""
        
        text = "**Possible Ingredient Substitutions:**\n\n"
        
        for item in suggestions:
            original = item.get("original", "")
            subs = item.get("substitutions", [])
            
            if original and subs:
                text += f"For {original}, you could use:\n"
                
                for sub in subs[:3]:  # Limit to top 3 substitutions
                    name = sub.get("name", "")
                    notes = sub.get("notes", "")
                    
                    if notes:
                        text += f"• {name} ({notes})\n"
                    else:
                        text += f"• {name}\n"
                
                text += "\n"
        
        return text

# Create substitution engine instance
substitution_engine = RecipeSubstitutionEngine() 