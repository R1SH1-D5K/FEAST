from fastapi import FastAPI, Request, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
import asyncio
import uvicorn
from rasa.core.agent import Agent
from rasa.shared.utils.io import json_to_string
import logging
import json
from fastapi.responses import JSONResponse
import uuid
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Recipe Chatbot API",
    description="API for interacting with the Recipe Chatbot",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=json.loads(os.getenv("CORS_ORIGINS", '["*"]')),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting
class RateLimiter:
    def __init__(self, requests_per_minute=60):
        self.requests_per_minute = requests_per_minute
        self.request_history = {}
    
    async def check_rate_limit(self, client_ip: str) -> bool:
        current_time = datetime.now()
        
        # Clean up old entries
        self.request_history = {ip: times for ip, times in self.request_history.items() 
                               if times[-1] > current_time - timedelta(minutes=1)}
        
        # Check if client has history
        if client_ip not in self.request_history:
            self.request_history[client_ip] = [current_time]
            return True
        
        # Check if client has exceeded rate limit
        times = self.request_history[client_ip]
        if len(times) >= self.requests_per_minute:
            oldest_allowed_time = current_time - timedelta(minutes=1)
            if times[0] > oldest_allowed_time:
                return False
            
            # Remove oldest request
            times.pop(0)
        
        # Add current request
        times.append(current_time)
        return True

rate_limiter = RateLimiter()

# API key security (optional)
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key: str = Header(None, alias=API_KEY_NAME)):
    if os.getenv("API_KEY_REQUIRED", "false").lower() == "true":
        if api_key is None or api_key != os.getenv("API_KEY"):
            raise HTTPException(status_code=403, detail="Invalid API Key")
    return api_key

# Load the Rasa agent
agent = None

@app.on_event("startup")
async def startup_event():
    global agent
    model_path = "./models"
    agent = await Agent.load(model_path)
    logger.info("Rasa agent loaded successfully")

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware"""
    client_ip = request.client.host
    
    # Skip rate limiting for certain endpoints
    if request.url.path == "/health":
        return await call_next(request)
    
    # Check rate limit
    if not await rate_limiter.check_rate_limit(client_ip):
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Please try again later."}
        )
    
    # Process the request
    return await call_next(request)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests for debugging"""
    start_time = time.time()
    
    # Generate request ID
    request_id = str(uuid.uuid4())
    
    # Log request details
    logger.info(f"Request {request_id}: {request.method} {request.url}")
    
    try:
        # Process the request
        response = await call_next(request)
        
        # Log response details
        process_time = time.time() - start_time
        logger.info(f"Response {request_id}: {response.status_code} (took {process_time:.4f}s)")
        
        return response
    except Exception as e:
        logger.error(f"Error processing request {request_id}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "error": str(e)}
        )

def format_response_for_ui(response, slots=None):
    """Format the Rasa response for UI consumption"""
    formatted_response = {
        "messages": [],
        "suggestions": []
    }
    
    # Extract text messages
    for msg in response:
        if msg.get("text"):
            formatted_response["messages"].append({
                "type": "text",
                "content": msg.get("text")
            })
    
    # Generate suggestions based on current context
    if slots:
        suggestions = []
        
        # Diet-based suggestions
        if slots.get("diet"):
            diet = slots.get("diet")
            suggestions.extend([
                f"Show me {diet} desserts",
                f"I want quick {diet} meals",
                f"What {diet} Italian dishes can I make?"
            ])
        
        # Cuisine-based suggestions
        if slots.get("cuisine"):
            cuisine = slots.get("cuisine")
            suggestions.extend([
                f"What {cuisine} desserts can I make?",
                f"Show me quick {cuisine} recipes",
                f"I want vegetarian {cuisine} food"
            ])
        
        # Generic suggestions if no context
        if not suggestions:
            suggestions = [
                "Show me vegetarian recipes",
                "What can I make in 30 minutes?",
                "I want Italian food",
                "Show me dessert recipes",
                "What can I cook with chicken and rice?"
            ]
        
        # Add clear preferences suggestion
        suggestions.append("Clear my preferences")
        
        # Add to formatted response
        formatted_response["suggestions"] = suggestions[:5]  # Limit to 5 suggestions
    
    return formatted_response

@app.post("/chat", dependencies=[Depends(get_api_key)])
async def chat(request: Request):
    """Enhanced chat endpoint with detailed response structure"""
    data = await request.json()
    user_message = data.get("message", "")
    sender_id = data.get("sender_id", "default")
    
    if not user_message:
        return {
            "status": "error",
            "message": "Please provide a message",
            "formatted_response": {
                "messages": [{"type": "text", "content": "Please provide a message"}],
                "suggestions": []
            }
        }
    
    try:
        # Process the message with Rasa
        response = await agent.handle_text(user_message, sender_id=sender_id)
        
        # Get the current slots
        tracker = agent.tracker_store.get_or_create_tracker(sender_id)
        slots = {key: value for key, value in tracker.current_slot_values().items() 
                if key in ["diet", "cuisine", "ingredient", "course", "time", "taste", "exclude_ingredient"]}
        
        # Format the response for UI consumption
        formatted_response = format_response_for_ui(response, slots)
        
        return {
            "status": "success",
            "message": "Message processed successfully",
            "response": response,
            "slots": slots,
            "formatted_response": formatted_response,
            "conversation_id": sender_id,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        return {
            "status": "error",
            "message": str(e),
            "formatted_response": {
                "messages": [{"type": "text", "content": f"Sorry, I encountered an error: {str(e)}"}],
                "suggestions": ["Try a simpler query", "Clear my preferences", "Show me some recipes"]
            },
            "timestamp": datetime.now().isoformat()
        }

@app.post("/clear_preferences")
async def clear_preferences(request: Request):
    """Clear user preferences"""
    data = await request.json()
    sender_id = data.get("sender_id", "default")
    
    try:
        response = await agent.handle_text("clear preferences", sender_id=sender_id)
        
        return {
            "status": "success",
            "message": "Preferences cleared successfully",
            "response": response
        }
    except Exception as e:
        logger.error(f"Error clearing preferences: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

@app.get("/recipes")
async def get_recipes(request: Request):
    """Get recipes based on query parameters with enhanced error handling"""
    params = dict(request.query_params)
    
    try:
        # Convert query parameters to preferences
        preferences = {}
        for key, value in params.items():
            if key in ["diet", "cuisine", "ingredient", "course", "time", "taste", "exclude_ingredient"]:
                preferences[key] = value
        
        # Search for recipes
        from recipe_db import search_with_fallback
        search_result = search_with_fallback(preferences)
        recipes = search_result["results"]
        relaxed = search_result["relaxed"]
        
        return {
            "status": "success", 
            "recipes": recipes,
            "relaxed_constraints": relaxed,
            "count": len(recipes)
        }
    except Exception as e:
        logger.error(f"Error getting recipes: {e}")
        return {
            "status": "error", 
            "message": str(e),
            "recipes": [],
            "count": 0
        }

@app.post("/feedback")
async def collect_feedback(request: Request):
    """Collect user feedback about the chatbot"""
    data = await request.json()
    
    feedback = {
        "user_id": data.get("user_id", "anonymous"),
        "rating": data.get("rating"),
        "message": data.get("message", ""),
        "conversation_id": data.get("conversation_id", ""),
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        # Store feedback in MongoDB
        from pymongo import MongoClient
        import os
        
        mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
        client = MongoClient(mongo_uri)
        db = client["recipeDB"]
        db["feedback"].insert_one(feedback)
        
        # Also log it
        logger.info(f"Received feedback: {feedback}")
        
        return {"status": "success", "message": "Feedback received, thank you!"}
    except Exception as e:
        logger.error(f"Error storing feedback: {e}")
        # Still acknowledge receipt even if storage fails
        return {"status": "partial", "message": "Feedback received but not stored"}

@app.get("/health")
async def health_check():
    """Health check endpoint with detailed status"""
    try:
        # Check if agent is loaded
        agent_status = agent is not None
        
        # Check MongoDB connection
        db_status = False
        try:
            from pymongo import MongoClient
            import os
            
            mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
            client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
            client.server_info()  # Will raise exception if cannot connect
            db_status = True
        except:
            db_status = False
        
        return {
            "status": "healthy" if agent_status else "degraded",
            "agent_loaded": agent_status,
            "database_connected": db_status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 