import logging
import numpy as np
from typing import Dict, List, Any, Optional
import os
import json
from collections import defaultdict

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RecipeRecommender:
    """Recipe recommendation engine using collaborative filtering"""
    
    def __init__(self):
        self.user_preferences = {}
        self.recipe_features = {}
        self.recipe_similarity = {}
        self.load_data()
    
    def load_data(self):
        """Load user preferences and recipe features"""
        try:
            # Load user preferences if available
            if os.path.exists("data/user_preferences.json"):
                with open("data/user_preferences.json", "r") as f:
                    self.user_preferences = json.load(f)
                logger.info(f"Loaded preferences for {len(self.user_preferences)} users")
            
            # Load recipe features if available
            if os.path.exists("data/recipe_features.json"):
                with open("data/recipe_features.json", "r") as f:
                    self.recipe_features = json.load(f)
                logger.info(f"Loaded features for {len(self.recipe_features)} recipes")
            
            # Compute recipe similarity matrix
            self._compute_recipe_similarity()
        except Exception as e:
            logger.error(f"Error loading recommendation data: {e}")
    
    def _compute_recipe_similarity(self):
        """Compute similarity between recipes based on features"""
        if not self.recipe_features:
            return
        
        # Convert features to vectors
        recipe_ids = list(self.recipe_features.keys())
        feature_names = set()
        
        # Collect all possible feature names
        for features in self.recipe_features.values():
            feature_names.update(features.keys())
        
        feature_names = list(feature_names)
        
        # Create feature vectors
        vectors = {}
        for recipe_id in recipe_ids:
            vector = []
            features = self.recipe_features.get(recipe_id, {})
            
            for feature in feature_names:
                vector.append(features.get(feature, 0))
            
            vectors[recipe_id] = np.array(vector)
        
        # Compute cosine similarity
        similarity = {}
        for i, recipe1 in enumerate(recipe_ids):
            similarity[recipe1] = {}
            vec1 = vectors[recipe1]
            
            for j, recipe2 in enumerate(recipe_ids):
                if i == j:
                    similarity[recipe1][recipe2] = 1.0
                    continue
                
                vec2 = vectors[recipe2]
                
                # Compute cosine similarity
                dot_product = np.dot(vec1, vec2)
                norm1 = np.linalg.norm(vec1)
                norm2 = np.linalg.norm(vec2)
                
                if norm1 == 0 or norm2 == 0:
                    similarity[recipe1][recipe2] = 0.0
                else:
                    similarity[recipe1][recipe2] = dot_product / (norm1 * norm2)
        
        self.recipe_similarity = similarity
        logger.info("Computed recipe similarity matrix")
    
    def update_user_preferences(self, user_id: str, recipe_id: str, rating: float):
        """Update user preferences with a new rating"""
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = {}
        
        self.user_preferences[user_id][recipe_id] = rating
        
        # Save updated preferences
        try:
            os.makedirs("data", exist_ok=True)
            with open("data/user_preferences.json", "w") as f:
                json.dump(self.user_preferences, f)
        except Exception as e:
            logger.error(f"Error saving user preferences: {e}")
    
    def get_similar_recipes(self, recipe_id: str, n: int = 5) -> List[str]:
        """Get n most similar recipes to the given recipe"""
        if recipe_id not in self.recipe_similarity:
            return []
        
        # Get similarity scores
        similarities = self.recipe_similarity[recipe_id]
        
        # Sort by similarity (descending)
        similar_recipes = sorted(similarities.items(), key=lambda x: x[1], reverse=True)
        
        # Return top n (excluding the recipe itself)
        return [r[0] for r in similar_recipes[1:n+1]]
    
    def get_personalized_recommendations(self, user_id: str, n: int = 5) -> List[str]:
        """Get personalized recipe recommendations for a user"""
        if user_id not in self.user_preferences:
            return []
        
        # Get user ratings
        user_ratings = self.user_preferences[user_id]
        
        # Calculate predicted ratings for unrated recipes
        predicted_ratings = {}
        
        for recipe_id in self.recipe_features:
            # Skip already rated recipes
            if recipe_id in user_ratings:
                continue
            
            # Calculate predicted rating using item-based collaborative filtering
            numerator = 0
            denominator = 0
            
            for rated_recipe, rating in user_ratings.items():
                if rated_recipe in self.recipe_similarity and recipe_id in self.recipe_similarity[rated_recipe]:
                    similarity = self.recipe_similarity[rated_recipe][recipe_id]
                    numerator += similarity * rating
                    denominator += abs(similarity)
            
            if denominator > 0:
                predicted_ratings[recipe_id] = numerator / denominator
        
        # Sort by predicted rating (descending)
        recommendations = sorted(predicted_ratings.items(), key=lambda x: x[1], reverse=True)
        
        # Return top n recipe IDs
        return [r[0] for r in recommendations[:n]]
    
    def extract_recipe_features(self, recipe: Dict[str, Any]) -> Dict[str, float]:
        """Extract features from a recipe for similarity calculation"""
        features = {}
        
        # Extract cuisine
        cuisine = recipe.get("Cuisine", "").lower()
        if cuisine:
            features[f"cuisine_{cuisine}"] = 1.0
        
        # Extract diet type
        diet = recipe.get("diet", "").lower()
        if diet:
            features[f"diet_{diet}"] = 1.0
        
        # Extract course
        course = recipe.get("course", "").lower()
        if course:
            features[f"course_{course}"] = 1.0
        
        # Extract ingredients
        ingredients = recipe.get("ingredients", [])
        ingredient_counts = defaultdict(int)
        
        for ingredient in ingredients:
            # Simplify ingredient (remove quantities, etc.)
            simple_ingredient = ' '.join([word for word in ingredient.lower().split() 
                                         if not word.isdigit() and word not in ['cup', 'cups', 'tablespoon', 
                                                                               'tablespoons', 'teaspoon', 'teaspoons']])
            
            ingredient_counts[simple_ingredient] += 1
        
        # Add ingredient features
        for ingredient, count in ingredient_counts.items():
            features[f"ingredient_{ingredient}"] = min(count, 3) / 3.0  # Normalize
        
        # Extract cooking time if available
        time_str = recipe.get("time", "")
        if time_str:
            try:
                # Try to extract minutes
                import re
                time_match = re.search(r'(\d+)\s*min', time_str.lower())
                if time_match:
                    minutes = int(time_match.group(1))
                    # Normalize time: 0-30 min -> 0-0.5, 30-60 min -> 0.5-1.0, >60 min -> >1.0
                    features["time"] = min(minutes / 60.0, 2.0)
            except:
                pass
        
        return features
    
    def update_recipe_features(self, recipe_id: str, recipe: Dict[str, Any]):
        """Update features for a recipe"""
        features = self.extract_recipe_features(recipe)
        self.recipe_features[recipe_id] = features
        
        # Update similarity matrix
        self._compute_recipe_similarity()
        
        # Save updated features
        try:
            os.makedirs("data", exist_ok=True)
            with open("data/recipe_features.json", "w") as f:
                json.dump(self.recipe_features, f)
        except Exception as e:
            logger.error(f"Error saving recipe features: {e}")

# Initialize the recommender
recommender = RecipeRecommender() 