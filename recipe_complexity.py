import logging
from typing import Dict, List, Any, Optional
import re
import math

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RecipeComplexityAnalyzer:
    """Analyze recipe complexity based on various factors"""
    
    # Complexity indicators in instructions
    COMPLEX_TECHNIQUES = [
        "sous vide", "emulsify", "temper", "fold", "knead", "proof", "ferment",
        "reduce", "deglaze", "blanch", "braise", "caramelize", "flambe", "julienne",
        "marinate", "poach", "render", "sear", "simmer", "whip", "clarify"
    ]
    
    # Equipment that indicates complexity
    COMPLEX_EQUIPMENT = [
        "stand mixer", "food processor", "blender", "immersion blender", 
        "pressure cooker", "instant pot", "sous vide", "mandoline", "thermometer",
        "dutch oven", "cast iron", "pastry bag", "kitchen torch", "mortar and pestle"
    ]
    
    def __init__(self):
        # Complexity weights for different factors
        self.weights = {
            "ingredient_count": 0.3,
            "instruction_count": 0.2,
            "instruction_length": 0.1,
            "techniques": 0.2,
            "equipment": 0.1,
            "time": 0.1
        }
    
    def analyze_recipe(self, recipe: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze recipe complexity and return a complexity score and breakdown"""
        if not recipe:
            return {"score": 0, "level": "unknown", "factors": {}}
        
        # Extract recipe components
        ingredients = recipe.get("ingredients", [])
        instructions = recipe.get("instructions", [])
        time_str = recipe.get("time", "")
        
        # Calculate individual complexity factors
        factors = {}
        
        # Ingredient count factor (0-1)
        ingredient_count = len(ingredients)
        factors["ingredient_count"] = min(ingredient_count / 20, 1.0)
        
        # Instruction count factor (0-1)
        instruction_count = len(instructions)
        factors["instruction_count"] = min(instruction_count / 15, 1.0)
        
        # Instruction length factor (0-1)
        instruction_text = " ".join(instructions)
        instruction_words = len(instruction_text.split())
        factors["instruction_length"] = min(instruction_words / 300, 1.0)
        
        # Techniques factor (0-1)
        technique_count = 0
        for technique in self.COMPLEX_TECHNIQUES:
            if technique in instruction_text.lower():
                technique_count += 1
        factors["techniques"] = min(technique_count / 5, 1.0)
        
        # Equipment factor (0-1)
        equipment_count = 0
        for equipment in self.COMPLEX_EQUIPMENT:
            if equipment in instruction_text.lower():
                equipment_count += 1
        factors["equipment"] = min(equipment_count / 3, 1.0)
        
        # Time factor (0-1)
        minutes = self._extract_time_minutes(time_str)
        factors["time"] = min(minutes / 120, 1.0)  # Cap at 2 hours
        
        # Calculate weighted score
        score = 0
        for factor, value in factors.items():
            score += value * self.weights.get(factor, 0)
        
        # Determine complexity level
        level = "easy"
        if score > 0.7:
            level = "hard"
        elif score > 0.4:
            level = "medium"
        
        return {
            "score": round(score, 2),
            "level": level,
            "factors": {k: round(v, 2) for k, v in factors.items()}
        }
    
    def get_complexity_explanation(self, complexity: Dict[str, Any]) -> str:
        """Generate a human-readable explanation of recipe complexity"""
        if not complexity:
            return "Unable to determine recipe complexity."
        
        score = complexity.get("score", 0)
        level = complexity.get("level", "unknown")
        factors = complexity.get("factors", {})
        
        explanation = f"This recipe is rated as {level} difficulty (score: {score}).\n\n"
        
        # Explain the main contributing factors
        if factors:
            explanation += "Key factors:\n"
            
            # Sort factors by contribution
            sorted_factors = sorted(
                [(k, v) for k, v in factors.items()], 
                key=lambda x: x[1], 
                reverse=True
            )
            
            for factor, value in sorted_factors[:3]:
                if value > 0.3:
                    explanation += self._get_factor_explanation(factor, value)
        
        return explanation
    
    def _get_factor_explanation(self, factor: str, value: float) -> str:
        """Get explanation for a specific complexity factor"""
        explanations = {
            "ingredient_count": "• Uses many ingredients\n",
            "instruction_count": "• Has many preparation steps\n",
            "instruction_length": "• Detailed and lengthy instructions\n",
            "techniques": "• Requires advanced cooking techniques\n",
            "equipment": "• Requires specialized kitchen equipment\n",
            "time": "• Takes significant time to prepare\n"
        }
        
        return explanations.get(factor, f"• {factor.replace('_', ' ').title()}: {value}\n")
    
    def _extract_time_minutes(self, time_str: str) -> int:
        """Extract cooking time in minutes from string"""
        if not time_str:
            return 60  # Default
        
        time_str = time_str.lower()
        
        # Try to extract minutes
        minutes_match = re.search(r'(\d+)\s*min', time_str)
        if minutes_match:
            return int(minutes_match.group(1))
        
        # Try to extract hours and convert to minutes
        hours_match = re.search(r'(\d+)\s*hour', time_str)
        if hours_match:
            return int(hours_match.group(1)) * 60
        
        # If no match, return default
        return 60

# Create analyzer instance
complexity_analyzer = RecipeComplexityAnalyzer() 