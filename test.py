from pymongo import MongoClient

mongo_uri = "mongodb://localhost:27017/"
client = MongoClient(mongo_uri)
db = client["recipeDB"]
collection = db["recipes"]

recipe = db.recipes.find_one()
print(recipe)
