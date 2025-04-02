from recipe_complexity import complexity_analyzer
from recipe_substitution import substitution_engine
from recipe_scaling import recipe_scaler
from recipe_filter import recipe_filter
from nutritional_analysis import extract_nutritional_requirements, meets_nutritional_requirements, get_nutritional_summary

def get_enhanced_recipe(recipe_id: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
    """Get a recipe with enhanced information"""
    if not options:
        options = {}
    
    # Get the basic recipe
    recipe = get_recipe(recipe_id)
    if not recipe:
        return {}
    
    # Apply scaling if requested
    scale_factor = options.get("scale_factor")
    if scale_factor and float(scale_factor) > 0:
        recipe = recipe_scaler.scale_recipe(recipe, float(scale_factor))
    
    # Add complexity analysis
    recipe["complexity"] = complexity_analyzer.analyze_recipe(recipe)
    
    # Add substitution suggestions
    diet = options.get("diet")
    recipe["substitutions"] = substitution_engine.suggest_recipe_substitutions(recipe, diet)
    
    # Add nutritional summary
    recipe["nutritional_summary"] = get_nutritional_summary(recipe)
    
    return recipe

def search_recipes_advanced(query: Dict[str, Any]) -> Dict[str, Any]:
    """Advanced recipe search with filtering, sorting, and nutritional requirements"""
    # Extract basic search parameters
    preferences = {k: v for k, v in query.items() if k in [
        "diet", "cuisine", "ingredient", "course", "time", "taste", "exclude_ingredient"
    ]}
    
    # Extract advanced parameters
    sort_by = query.get("sort_by", "name")
    ascending = query.get("ascending", True)
    limit = int(query.get("limit", 10))
    offset = int(query.get("offset", 0))
    
    # Extract nutritional requirements
    nutritional_text = query.get("nutritional_text", "")
    nutritional_requirements = extract_nutritional_requirements(nutritional_text)
    
    # Perform basic search
    search_results = search_with_weighted_scoring(preferences)
    recipes = search_results.get("results", [])
    
    # Apply nutritional filtering
    if nutritional_requirements:
        recipes = [r for r in recipes if meets_nutritional_requirements(r, nutritional_requirements)]
    
    # Apply additional filtering
    filters = {}
    if "max_time" in query:
        filters["max_time"] = int(query["max_time"])
    if "max_calories" in query:
        filters["max_calories"] = int(query["max_calories"])
    if "min_protein" in query:
        filters["min_protein"] = int(query["min_protein"])
    if "min_rating" in query:
        filters["rating"] = float(query["min_rating"])
    
    if filters:
        recipes = recipe_filter.filter_recipes(recipes, filters)
    
    # Sort results
    recipes = recipe_filter.sort_recipes(recipes, sort_by, ascending)
    
    # Apply pagination
    total_count = len(recipes)
    recipes = recipes[offset:offset+limit]
    
    return {
        "results": recipes,
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
        "has_more": offset + limit < total_count
    } 