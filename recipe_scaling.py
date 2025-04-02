import logging
from typing import Dict, List, Any, Optional
import re
from fractions import Fraction

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RecipeScaler:
    """Scale recipe ingredients up or down"""
    
    # Units that should be scaled
    SCALABLE_UNITS = [
        "cup", "cups", "tablespoon", "tablespoons", "tbsp", "teaspoon", "teaspoons", "tsp",
        "ounce", "ounces", "oz", "pound", "pounds", "lb", "gram", "grams", "g",
        "kilogram", "kilograms", "kg", "milliliter", "milliliters", "ml",
        "liter", "liters", "l", "quart", "quarts", "qt", "pint", "pints", "pt",
        "gallon", "gallons", "gal"
    ]
    
    # Units that should not be scaled (or scaled differently)
    NON_SCALABLE_UNITS = [
        "pinch", "pinches", "dash", "dashes", "to taste", "as needed"
    ]
    
    def scale_recipe(self, recipe: Dict[str, Any], scale_factor: float) -> Dict[str, Any]:
        """Scale a recipe by the given factor"""
        if not recipe or scale_factor <= 0:
            return recipe
        
        # Create a copy of the recipe to modify
        scaled_recipe = recipe.copy()
        
        # Scale ingredients
        original_ingredients = recipe.get("ingredients", [])
        scaled_ingredients = []
        
        for ingredient in original_ingredients:
            scaled_ingredient = self.scale_ingredient(ingredient, scale_factor)
            scaled_ingredients.append(scaled_ingredient)
        
        scaled_recipe["ingredients"] = scaled_ingredients
        
        # Update servings if present
        if "servings" in recipe:
            try:
                original_servings = int(recipe["servings"])
                scaled_recipe["servings"] = max(1, round(original_servings * scale_factor))
            except (ValueError, TypeError):
                # If servings is not a number, leave it as is
                pass
        
        # Add scaling note
        scaled_recipe["scaling_note"] = f"Recipe scaled by {scale_factor:.1f}x from original"
        
        return scaled_recipe
    
    def scale_ingredient(self, ingredient: str, scale_factor: float) -> str:
        """Scale a single ingredient by the given factor"""
        if not ingredient:
            return ingredient
        
        # Check if this is a non-scalable ingredient
        if any(term in ingredient.lower() for term in self.NON_SCALABLE_UNITS):
            return ingredient
        
        # Try to extract quantity and unit
        quantity_match = re.search(r'^([\d\s./]+)', ingredient)
        
        if not quantity_match:
            return ingredient  # No quantity found
        
        quantity_str = quantity_match.group(1).strip()
        
        try:
            # Handle fractions like "1/2"
            if '/' in quantity_str and ' ' not in quantity_str:
                quantity = float(Fraction(quantity_str))
            # Handle mixed numbers like "1 1/2"
            elif '/' in quantity_str and ' ' in quantity_str:
                whole, frac = quantity_str.split(' ', 1)
                quantity = int(whole) + float(Fraction(frac))
            # Handle decimal numbers
            else:
                quantity = float(quantity_str)
            
            # Scale the quantity
            scaled_quantity = quantity * scale_factor
            
            # Format the scaled quantity
            if scaled_quantity.is_integer():
                scaled_str = str(int(scaled_quantity))
            elif scaled_quantity < 0.125:
                scaled_str = "a pinch"  # Very small amounts
            else:
                # Try to convert to a fraction for common cooking measurements
                fraction = self._decimal_to_fraction(scaled_quantity)
                if fraction:
                    scaled_str = fraction
                else:
                    scaled_str = f"{scaled_quantity:.2f}".rstrip('0').rstrip('.')
            
            # Replace the original quantity with the scaled quantity
            return re.sub(r'^([\d\s./]+)', scaled_str, ingredient, 1)
        
        except (ValueError, ZeroDivisionError):
            return ingredient  # If we can't parse the quantity, return the original
    
    def _decimal_to_fraction(self, decimal: float) -> Optional[str]:
        """Convert a decimal to a common cooking fraction if possible"""
        # Common cooking fractions
        fractions = {
            0.125: "1/8",
            0.25: "1/4",
            0.33: "1/3",
            0.375: "3/8",
            0.5: "1/2",
            0.625: "5/8",
            0.66: "2/3",
            0.75: "3/4",
            0.875: "7/8"
        }
        
        # Handle whole numbers with fractions
        whole_part = int(decimal)
        decimal_part = decimal - whole_part
        
        # Find the closest fraction
        closest_fraction = None
        min_diff = float('inf')
        
        for frac_decimal, frac_str in fractions.items():
            diff = abs(decimal_part - frac_decimal)
            if diff < min_diff and diff < 0.05:  # Within 5% tolerance
                min_diff = diff
                closest_fraction = frac_str
        
        if closest_fraction:
            if whole_part > 0:
                return f"{whole_part} {closest_fraction}"
            else:
                return closest_fraction
        
        return None

# Create scaler instance
recipe_scaler = RecipeScaler() 