from typing import Any, Dict, List, Text
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
import logging
from pymongo import MongoClient
import os
import re
import yaml
import json
import random

# Set up logging
logger = logging.getLogger(__name__)

# MongoDB connection
mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(mongo_uri)
db = client["recipeDB"]  # Your database name
collection = db["recipes"]  # Your collection name

# Define taxonomies at the top of your file
INGREDIENT_CATEGORIES = {
    "pasta": ["pasta", "spaghetti", "penne", "fettuccine", "linguine", "macaroni", 
              "lasagna", "ravioli", "tortellini", "farfalle", "rigatoni", "orzo"],
    "rice": ["rice", "risotto", "biryani", "pilaf", "fried rice"],
    "meat": ["chicken", "beef", "pork", "mutton", "lamb", "turkey"],
    "seafood": ["fish", "shrimp", "prawn", "crab", "lobster", "salmon", "tuna"],
    # Add more categories
}

DIET_EXCLUSIONS = {
    "vegetarian": INGREDIENT_CATEGORIES["meat"] + INGREDIENT_CATEGORIES["seafood"],
    "vegan": (INGREDIENT_CATEGORIES["meat"] + INGREDIENT_CATEGORIES["seafood"] + 
              ["milk", "cheese", "cream", "egg", "butter", "yogurt"]),
    "gluten-free": ["wheat", "barley", "rye", "flour", "pasta", "bread", "cereal"],
    # Add more diets
}

class ActionSearchRecipes(Action):
    def name(self) -> Text:
        return "action_search_recipes"

    def extract_complex_preferences(self, tracker):
        """Extract and normalize complex preferences from user input"""
        # Get basic slots
        preferences = {
            "diet": tracker.get_slot("diet"),
            "cuisine": tracker.get_slot("cuisine"),
            "ingredient": tracker.get_slot("ingredient"),
            "course": tracker.get_slot("course"),
            "time": tracker.get_slot("time"),
            "taste": tracker.get_slot("taste"),
            "exclude_ingredient": tracker.get_slot("exclude_ingredient")
        }
        
        # Remove None values
        preferences = {k: v for k, v in preferences.items() if v is not None}
        
        # Handle negations in the latest message
        latest_message = tracker.latest_message.get("text", "").lower()
        
        # Check for negations related to ingredients
        negation_patterns = [
            r"without ([a-zA-Z ]+)",
            r"no ([a-zA-Z ]+)",
            r"don't want ([a-zA-Z ]+)",
            r"not ([a-zA-Z ]+)"
        ]
        
        for pattern in negation_patterns:
            matches = re.findall(pattern, latest_message)
            for match in matches:
                preferences["exclude_ingredient"] = match.strip()
        
        return preferences

    def run(self, dispatcher, tracker, domain):
        # Extract preferences from slots and message
        preferences = self.extract_complex_preferences(tracker)
        
        # Check if we need to ask for more information to refine the search
        if self.handle_progressive_slot_filling(dispatcher, tracker, preferences):
            return []
            
        # Check if we need to handle ambiguous queries
        if self.handle_ambiguous_query(dispatcher, tracker, preferences):
            return []
        
        # Check if we have any preferences
        if preferences:
            logger.info(f"Searching for recipes with preferences: {preferences}")
            
            # Check if user is asking for recipes with available ingredients
            if "available_ingredients" in preferences:
                ingredients = preferences["available_ingredients"].split(",")
                ingredients = [ing.strip() for ing in ingredients]
                
                from recipe_db import search_by_available_ingredients
                recipes = search_by_available_ingredients(ingredients)
                
                if recipes:
                    dispatcher.utter_message(text=f"I found {len(recipes)} recipes you can make with your ingredients:")
                    
                    # Choose a recipe to display
                    recipe = recipes[0]  # Show the best match
                    
                    # Format the recipe with substitutions
                    from recipe_db import format_recipe_with_substitutions
                    recipe_text = format_recipe_with_substitutions(recipe)
                    
                    # Personalize the response
                    self.personalize_response(dispatcher, tracker, recipe_text)
                    
                    return [
                        SlotSet("last_query", json.dumps(preferences)),
                        SlotSet("skip_count", 1)  # We've shown 1 recipe
                    ]
                else:
                    dispatcher.utter_message(text="I couldn't find any recipes with those ingredients. Try adding more ingredients or relaxing your constraints.")
                    return []
            
            # Search for recipes with fallback
            from recipe_db import search_with_fallback
            search_result = search_with_fallback(preferences)
            recipes = search_result["results"]
            relaxed = search_result["relaxed"]
            
            if recipes:
                # If we had to relax constraints, let the user know
                if relaxed:
                    relaxed_str = ", ".join(relaxed)
                    dispatcher.utter_message(text=f"I couldn't find recipes matching all your criteria, so I relaxed the {relaxed_str} requirements.")
                
                # Choose a random recipe to display
                recipe = random.choice(recipes)
                
                # Format the recipe with substitutions
                from recipe_db import format_recipe_with_substitutions
                recipe_text = format_recipe_with_substitutions(recipe)
                
                # Personalize the response
                self.personalize_response(dispatcher, tracker, recipe_text)
                
                # Store the search parameters for pagination
                return [
                    SlotSet("last_query", json.dumps(preferences)),
                    SlotSet("skip_count", 1)  # We've shown 1 recipe
                ]
            else:
                dispatcher.utter_message(text="I couldn't find any recipes matching your criteria. Try relaxing some constraints.")
        else:
            dispatcher.utter_message(text="I couldn't find any specific preferences. What kind of recipes are you looking for?")
        
        return []
        
    def handle_progressive_slot_filling(self, dispatcher, tracker, preferences):
        """Handle progressive slot filling to refine user requests"""
        # If we have diet but no cuisine, ask for cuisine
        if preferences.get("diet") and not preferences.get("cuisine"):
            diet = preferences["diet"]
            dispatcher.utter_message(text=f"I can find {diet} recipes. Do you have a cuisine preference? For example, Italian, Indian, or Mexican?")
            return True
            
        # If we have cuisine but no course, ask for course
        if preferences.get("cuisine") and not preferences.get("course"):
            cuisine = preferences["cuisine"]
            dispatcher.utter_message(text=f"I can find {cuisine} recipes. What type of dish are you looking for? For example, appetizer, main course, or dessert?")
            return True
            
        # If we have course but no time constraint, ask about time
        if preferences.get("course") and not preferences.get("time"):
            course = preferences["course"]
            dispatcher.utter_message(text=f"Do you have any time constraints for your {course}? For example, quick meals or something that takes less than 30 minutes?")
            return True
            
        return False
        
    def handle_ambiguous_query(self, dispatcher, tracker, preferences):
        """Handle ambiguous queries by asking for clarification"""
        latest_message = tracker.latest_message.get("text", "").lower()
        
        # Check for ambiguous terms
        ambiguous_terms = {
            "pasta": ["Do you want a pasta main dish or a pasta salad?", "pasta_type"],
            "salad": ["Would you prefer a side salad or a main course salad?", "salad_type"],
            "cake": ["Are you looking for a birthday cake, a dessert cake, or a quick snack cake?", "cake_type"],
            "soup": ["Would you prefer a creamy soup or a broth-based soup?", "soup_type"],
            "sandwich": ["Are you looking for a hot sandwich or a cold sandwich?", "sandwich_type"]
        }
        
        for term, (question, slot) in ambiguous_terms.items():
            if term in latest_message and not tracker.get_slot(slot):
                dispatcher.utter_message(text=question)
                return True
        
        return False
        
    def personalize_response(self, dispatcher, tracker, recipe_text):
        """Personalize the response based on user history"""
        # Get user preferences from past interactions
        diet_count = 0
        quick_count = 0
        
        for event in tracker.events:
            if event.get("event") == "slot" and event.get("name") == "diet":
                diet_count += 1
            if event.get("event") == "slot" and event.get("name") == "time" and "quick" in str(event.get("value", "")).lower():
                quick_count += 1
        
        # Personalize based on patterns
        personalized_intro = "Here's a recipe I found for you:"
        
        if diet_count > 2:
            diet = tracker.get_slot("diet")
            if diet:
                personalized_intro = f"I know you prefer {diet} recipes. Here's one I think you'll like:"
        
        if quick_count > 2:
            personalized_intro = "Since you seem to prefer quick recipes, here's a time-saving option:"
        
        dispatcher.utter_message(text=personalized_intro)
        dispatcher.utter_message(text=recipe_text)

class ActionTest(Action):
    def name(self) -> Text:
        return "action_test"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        dispatcher.utter_message(text="Test action executed successfully!")
        return []

def contains_keyword(message, keyword):
    """Check if a message contains a keyword, handling various edge cases."""
    # Convert to lowercase and strip whitespace
    message = message.lower().strip()
    keyword = keyword.lower().strip()
    
    # Check for exact match, word boundary match, or substring match
    return (
        keyword == message or
        f" {keyword} " in f" {message} " or
        f" {keyword}," in f" {message} " or
        f" {keyword}." in f" {message} " or
        message.startswith(f"{keyword} ") or
        message.endswith(f" {keyword}") or
        keyword in message
    )

class ActionGetRecipes(Action):
    def name(self) -> Text:
        return "action_get_recipes"

    def run(
        self, 
        dispatcher: CollectingDispatcher, 
        tracker: Tracker, 
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        try:
            # Extract entities from the message
            entities = {}
            for entity in tracker.latest_message.get('entities', []):
                entity_type = entity['entity']
                entity_value = entity['value']
                
                # Handle multiple entities of the same type (like multiple ingredients)
                if entity_type in entities:
                    if isinstance(entities[entity_type], list):
                        entities[entity_type].append(entity_value)
                    else:
                        entities[entity_type] = [entities[entity_type], entity_value]
                else:
                    entities[entity_type] = entity_value
            
            logger.info(f"Extracted entities: {entities}")
            
            # Load taxonomy
            try:
                with open('recipe_taxonomy.yaml', 'r') as file:
                    taxonomy = yaml.safe_load(file)
                    ingredient_categories = taxonomy.get('ingredient_categories', {})
                    diet_exclusions = taxonomy.get('diet_exclusions', {})
            except Exception as e:
                logger.error(f"Error loading taxonomy: {str(e)}")
                ingredient_categories = INGREDIENT_CATEGORIES
                diet_exclusions = DIET_EXCLUSIONS
            
            # Initialize query
            query = {}
            
            # Process diet entities
            if 'diet' in entities:
                diet_values = entities['diet'] if isinstance(entities['diet'], list) else [entities['diet']]
                diet_conditions = []
                
                for diet in diet_values:
                    diet = diet.lower()
                    if diet in diet_exclusions:
                        exclusion_regex = "|".join(diet_exclusions[diet])
                        diet_conditions.append({"ingredients": {"$not": {"$regex": exclusion_regex, "$options": "i"}}})
                
                if len(diet_conditions) == 1:
                    query.update(diet_conditions[0])
                elif len(diet_conditions) > 1:
                    query["$and"] = diet_conditions
            
            # Process cuisine entities
            if 'cuisine' in entities:
                cuisine_values = entities['cuisine'] if isinstance(entities['cuisine'], list) else [entities['cuisine']]
                cuisine_regex = "|".join(cuisine_values)
                query["Cuisine"] = {"$regex": cuisine_regex, "$options": "i"}
            
            # Process ingredient entities
            if 'ingredient' in entities:
                ingredient_values = entities['ingredient'] if isinstance(entities['ingredient'], list) else [entities['ingredient']]
                ingredient_conditions = []
                
                for ingredient in ingredient_values:
                    ingredient = ingredient.lower()
                    # Check if it's a category or specific ingredient
                    expanded_ingredients = []
                    
                    # Check if it's a category name
                    if ingredient in ingredient_categories:
                        expanded_ingredients.extend(ingredient_categories[ingredient])
                    else:
                        # Check if it belongs to a category
                        for category, items in ingredient_categories.items():
                            if ingredient in items:
                                expanded_ingredients.extend(items)
                                break
                    
                    # If no category found, use the ingredient as is
                    if not expanded_ingredients:
                        expanded_ingredients = [ingredient]
                    
                    ingredient_regex = "|".join(expanded_ingredients)
                    ingredient_conditions.append({"ingredients": {"$regex": ingredient_regex, "$options": "i"}})
                
                if len(ingredient_conditions) == 1:
                    if "ingredients" in query and "$not" in query["ingredients"]:
                        # We already have diet exclusions, need to use $and
                        query = {"$and": [{"ingredients": query["ingredients"]}, ingredient_conditions[0]]}
                    else:
                        query.update(ingredient_conditions[0])
                elif len(ingredient_conditions) > 1:
                    if "ingredients" in query and "$not" in query["ingredients"]:
                        # We already have diet exclusions, need to use $and
                        query = {"$and": [{"ingredients": query["ingredients"]}, {"$and": ingredient_conditions}]}
                    else:
                        query["$and"] = ingredient_conditions
            
            # Process excluded ingredient entities
            if 'exclude_ingredient' in entities:
                exclude_values = entities['exclude_ingredient'] if isinstance(entities['exclude_ingredient'], list) else [entities['exclude_ingredient']]
                exclude_conditions = []
                
                for exclude in exclude_values:
                    exclude = exclude.lower()
                    exclude_conditions.append({"ingredients": {"$not": {"$regex": exclude, "$options": "i"}}})
                
                if "ingredients" in query and "$not" in query["ingredients"]:
                    # We already have diet exclusions, need to combine
                    if "$and" in query:
                        query["$and"].extend(exclude_conditions)
                    else:
                        query["$and"] = [{"ingredients": query["ingredients"]}] + exclude_conditions
                        del query["ingredients"]
                elif len(exclude_conditions) == 1:
                    query.update(exclude_conditions[0])
                elif len(exclude_conditions) > 1:
                    if "$and" in query:
                        query["$and"].extend(exclude_conditions)
                    else:
                        query["$and"] = exclude_conditions
            
            # Process course entities
            if 'course' in entities:
                course_values = entities['course'] if isinstance(entities['course'], list) else [entities['course']]
                course_regex = "|".join(course_values)
                # Look for course in recipe name or description
                course_query = {"$or": [
                    {"RecipeName": {"$regex": course_regex, "$options": "i"}},
                    {"Description": {"$regex": course_regex, "$options": "i"}}
                ]}
                
                if "$and" in query:
                    query["$and"].append(course_query)
                else:
                    query = {"$and": [query, course_query]} if query else course_query
            
            # Process time entities (quick, easy, etc.)
            if 'time' in entities:
                time_values = entities['time'] if isinstance(entities['time'], list) else [entities['time']]
                time_conditions = []
                
                for time_value in time_values:
                    time_value = time_value.lower()
                    if time_value in ['quick', 'fast', 'easy', 'simple']:
                        # For quick/easy recipes, look for total time < 30 minutes
                        time_conditions.append({"TotalTimeInMins": {"$lt": 30}})
                    elif 'minute' in time_value or 'min' in time_value:
                        # Extract number from strings like "30-minute" or "under 15 minutes"
                        import re
                        time_match = re.search(r'(\d+)', time_value)
                        if time_match:
                            minutes = int(time_match.group(1))
                            time_conditions.append({"TotalTimeInMins": {"$lt": minutes}})
                
                if time_conditions:
                    if len(time_conditions) == 1:
                        if "$and" in query:
                            query["$and"].append(time_conditions[0])
                        else:
                            query = {"$and": [query, time_conditions[0]]} if query else time_conditions[0]
                    else:
                        time_query = {"$or": time_conditions}
                        if "$and" in query:
                            query["$and"].append(time_query)
                        else:
                            query = {"$and": [query, time_query]} if query else time_query
            
            # If no entities were found, fall back to keyword matching
            if not query:
                # Get the latest user message
                user_message = tracker.latest_message.get('text', '').lower()
                logger.info(f"No entities found, falling back to keyword matching for: '{user_message}'")
                
                # Initialize query parameters
                query = {}
                
                # Check for dietary restrictions
                if contains_keyword(user_message, "vegetarian"):
                    logger.info("Matched vegetarian diet")
                    # Exclude meat and seafood
                    meat_regex = "chicken|beef|pork|mutton|lamb|turkey|duck|goat|veal|bacon|ham|sausage|meatball|ground beef|ground pork|ground chicken|ground turkey"
                    seafood_regex = "fish|shrimp|prawn|crab|lobster|salmon|tuna|cod|tilapia|sardines|anchovies|mussels|clams|oysters|scallops|squid|octopus"
                    query["ingredients"] = {"$not": {"$regex": f"{meat_regex}|{seafood_regex}", "$options": "i"}}
                elif contains_keyword(user_message, "vegan"):
                    logger.info("Matched vegan diet")
                    # Exclude meat, seafood, and animal products
                    meat_regex = "chicken|beef|pork|mutton|lamb|turkey|duck|goat|veal|bacon|ham|sausage|meatball|ground beef|ground pork|ground chicken|ground turkey"
                    seafood_regex = "fish|shrimp|prawn|crab|lobster|salmon|tuna|cod|tilapia|sardines|anchovies|mussels|clams|oysters|scallops|squid|octopus"
                    dairy_regex = "milk|cheese|cream|butter|yogurt|sour cream|cream cheese|cottage cheese|ricotta|mozzarella|parmesan|cheddar|feta|ghee"
                    egg_regex = "egg|eggs|egg white|egg yolk|boiled egg|fried egg|poached egg|scrambled egg|omelette"
                    query["ingredients"] = {"$not": {"$regex": f"{meat_regex}|{seafood_regex}|{dairy_regex}|{egg_regex}", "$options": "i"}}
                elif contains_keyword(user_message, "gluten-free") or contains_keyword(user_message, "gluten free"):
                    logger.info("Matched gluten-free diet")
                    # Exclude gluten-containing ingredients
                    gluten_regex = "wheat|barley|rye|flour|pasta|bread|cereal|couscous|bulgur|semolina|farina|durum|kamut|spelt|triticale|malt|beer"
                    query["ingredients"] = {"$not": {"$regex": gluten_regex, "$options": "i"}}
                
                # Check for cuisines
                if contains_keyword(user_message, "indian"):
                    logger.info("Matched Indian cuisine")
                    query["Cuisine"] = {"$regex": "Indian", "$options": "i"}
                elif contains_keyword(user_message, "italian"):
                    logger.info("Matched Italian cuisine")
                    query["Cuisine"] = {"$regex": "Italian", "$options": "i"}
                elif contains_keyword(user_message, "chinese"):
                    logger.info("Matched Chinese cuisine")
                    query["Cuisine"] = {"$regex": "Chinese", "$options": "i"}
                elif contains_keyword(user_message, "mexican"):
                    logger.info("Matched Mexican cuisine")
                    query["Cuisine"] = {"$regex": "Mexican", "$options": "i"}
                
                # Check for ingredients - handle more complex combinations
                ingredient_query = None
                if contains_keyword(user_message, "chicken") and "ingredients" not in query:
                    logger.info("Matched chicken ingredient")
                    ingredient_query = {"ingredients": {"$regex": "chicken", "$options": "i"}}
                elif contains_keyword(user_message, "pasta") and "ingredients" not in query:
                    logger.info("Matched pasta ingredient")
                    # More specific pasta regex that looks for common pasta types
                    pasta_regex = "pasta|spaghetti|penne|fettuccine|linguine|macaroni|lasagna|ravioli|tortellini|farfalle|rigatoni|orzo"
                    ingredient_query = {"ingredients": {"$regex": pasta_regex, "$options": "i"}}
                    # Also check recipe name for pasta
                    name_query = {"RecipeName": {"$regex": pasta_regex, "$options": "i"}}
                    # Combine with OR
                    ingredient_query = {"$or": [ingredient_query, name_query]}
                elif contains_keyword(user_message, "rice") and "ingredients" not in query:
                    logger.info("Matched rice ingredient")
                    ingredient_query = {"ingredients": {"$regex": "rice", "$options": "i"}}
                
                # Add ingredient query if it exists
                if ingredient_query:
                    if query:
                        # Combine with existing query using $and
                        query = {"$and": [query, ingredient_query]}
                    else:
                        query = ingredient_query
            
            # Log the final query
            logger.info(f"Final MongoDB query: {query}")
            
            # Execute the query
            limit = 3  # Number of recipes to return
            recipes = list(collection.find(query).limit(limit))
            
            if not recipes:
                dispatcher.utter_message(text="I couldn't find any recipes matching your criteria. Try a different search?")
                return []
            
            # Format and send the recipes
            for recipe in recipes:
                recipe_name = recipe.get("RecipeName", "Unnamed Recipe")
                ingredients = recipe.get("ingredients", ["Ingredients not available"])
                instructions = recipe.get("instructions", ["Instructions not available"])
                cuisine = recipe.get("Cuisine", "Unknown cuisine")
                total_time = recipe.get("TotalTimeInMins", "Unknown")
                
                # Format ingredients as a bulleted list
                ingredients_text = "\n• " + "\n• ".join(ingredients)
                
                # Format instructions as numbered steps
                instructions_text = ""
                for i, step in enumerate(instructions, 1):
                    instructions_text += f"\n{i}. {step}"
                
                # Create the message
                message = f"**{recipe_name}**\n\n"
                message += f"**Cuisine:** {cuisine}\n"
                message += f"**Total Time:** {total_time} minutes\n\n"
                message += f"**Ingredients:**{ingredients_text}\n\n"
                message += f"**Instructions:**{instructions_text}"
                
                dispatcher.utter_message(text=message)
            
            # Store the query for pagination
            try:
                # Convert query to string for storage
                query_str = json.dumps(query)
                return [
                    SlotSet("last_query", query_str),
                    SlotSet("skip_count", limit)  # Store how many recipes we've shown
                ]
            except Exception as e:
                logger.error(f"Error storing query: {str(e)}")
                return []
        
        except Exception as e:
            logger.error(f"Error processing entities: {str(e)}")
            dispatcher.utter_message(text="Sorry, I encountered an error while processing your request. Please try again later.")
        
        return []

class ActionClearPreferences(Action):
    def name(self) -> Text:
        return "action_clear_preferences"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Clear all slots
        dispatcher.utter_message(text="I've cleared all your preferences. What kind of recipes would you like to see now?")
        
        return [
            SlotSet("diet", None),
            SlotSet("cuisine", None),
            SlotSet("ingredient", None),
            SlotSet("course", None),
            SlotSet("time", None),
            SlotSet("taste", None),
            SlotSet("exclude_ingredient", None)
        ]

class ActionShowNextRecipe(Action):
    def name(self) -> Text:
        return "action_show_next_recipe"

    def run(
        self, 
        dispatcher: CollectingDispatcher, 
        tracker: Tracker, 
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        # Get the last query from a slot
        last_query = tracker.get_slot("last_query")
        skip_count = tracker.get_slot("skip_count") or 1  # Default to 1 if not set
        
        logger.info(f"Last query: {last_query}, Skip count: {skip_count}")
        
        if not last_query:
            dispatcher.utter_message(text="I don't have any previous search to continue from. Please ask for a specific recipe.")
            return []
        
        try:
            # Convert the stored string back to a dictionary
            import json
            query = json.loads(last_query)
            
            logger.info(f"Parsed query: {query}, Skip count: {skip_count}")
            
            # Get the next recipe using the skip count
            recipes = list(collection.find(query).skip(int(skip_count)).limit(1))
            
            if recipes and len(recipes) > 0:
                recipe = recipes[0]
                recipe_name = recipe.get("RecipeName", "Unknown Recipe")
                ingredients = recipe.get("ingredients", [])
                instructions = recipe.get("instructions", [])
                total_time = recipe.get("TotalTimeInMins", "Unknown")
                cuisine = recipe.get("Cuisine", "Various")
                
                logger.info(f"Found next recipe: {recipe_name}")
                
                # Format the response
                response = f"## {recipe_name}\n\n"
                response += f"**Cuisine:** {cuisine}\n"
                response += f"**Total Time:** {total_time} minutes\n\n"
                
                response += "**Ingredients:**\n"
                if isinstance(ingredients, list):
                    for ingredient in ingredients:
                        response += f"- {ingredient}\n"
                else:
                    response += f"{ingredients}\n"
                
                response += "\n**Instructions:**\n"
                if isinstance(instructions, list):
                    for i, step in enumerate(instructions, 1):
                        response += f"{i}. {step}\n"
                else:
                    response += f"{instructions}\n"
                
                dispatcher.utter_message(text=response)
                
                # Increment the skip count for next time
                new_skip_count = skip_count + 1
                logger.info(f"Updating skip count to {new_skip_count}")
                
                # Check if there are more recipes
                remaining = collection.count_documents(query) - new_skip_count
                if remaining > 0:
                    dispatcher.utter_message(text=f"I found {remaining} more recipes matching your criteria. Would you like to see another one?")
                
                return [SlotSet("skip_count", new_skip_count)]
            else:
                dispatcher.utter_message(text="I don't have any more recipes matching your criteria.")
                return [SlotSet("last_query", None), SlotSet("skip_count", 0)]
                
        except Exception as e:
            logger.error(f"Error showing next recipe: {str(e)}")
            dispatcher.utter_message(text="Sorry, I encountered an error while retrieving the next recipe.")
            # Log the full exception for debugging
            import traceback
            logger.error(f"Full exception: {traceback.format_exc()}")
            return []

class ActionShowPreviousRecipe(Action):
    def name(self) -> Text:
        return "action_show_previous_recipe"
        
    def run(self, dispatcher, tracker, domain):
        # Get the last shown recipe from the conversation history
        events = tracker.events
        last_recipe = None
        
        for event in reversed(events):
            if event.get("event") == "bot" and "**" in event.get("text", ""):
                last_recipe = event.get("text")
                break
        
        if last_recipe:
            dispatcher.utter_message(text="Here's that recipe again:")
            dispatcher.utter_message(text=last_recipe)
        else:
            dispatcher.utter_message(text="I don't have any previous recipes to show you. Let's find something new!")
        
        return []

# Add this to explicitly register your actions
actions = [
    ActionTest,
    ActionGetRecipes,
    ActionClearPreferences,
    ActionShowNextRecipe,
    ActionShowPreviousRecipe,
]

# Then use these in your query building
def build_query(entities):
    """Build a MongoDB query from extracted entities"""
    query = {}
    
    # Handle diet restrictions
    if "diet" in entities:
        diet = entities["diet"].lower()
        if diet in DIET_EXCLUSIONS:
            exclusion_regex = "|".join(DIET_EXCLUSIONS[diet])
            query["ingredients"] = {"$not": {"$regex": exclusion_regex, "$options": "i"}}
    
    # Handle ingredients
    if "ingredient" in entities:
        ingredient = entities["ingredient"].lower()
        for category, items in INGREDIENT_CATEGORIES.items():
            if ingredient in items or ingredient == category:
                ingredient_regex = "|".join(items)
                ingredient_query = {"ingredients": {"$regex": ingredient_regex, "$options": "i"}}
                if "ingredients" in query:
                    query = {"$and": [{"ingredients": query["ingredients"]}, ingredient_query]}
                else:
                    query["ingredients"] = {"$regex": ingredient_regex, "$options": "i"}
                break
    
    # Handle cuisine
    if "cuisine" in entities:
        query["Cuisine"] = {"$regex": entities["cuisine"], "$options": "i"}
    
    return query
