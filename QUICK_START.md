# Recipe Chatbot Quick Start Guide

This guide will help you quickly set up and test the recipe chatbot.

## Setup

### Prerequisites
- Python 3.8+
- MongoDB (optional)

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/recipe-chatbot.git
   cd recipe-chatbot
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Train the model:
   ```
   rasa train
   ```

### Running the Chatbot

#### Option 1: Using the batch script (Windows)
```
run_chatbot.bat
```

#### Option 2: Manual startup
1. Start the action server:
   ```
   rasa run actions
   ```

2. In a new terminal, start the API server:
   ```
   python api.py
   ```

3. In a new terminal, run the interactive demo:
   ```
   python demo_script.py --interactive
   ```

## Testing the Chatbot

### Example Queries
- "Show me vegetarian pasta recipes"
- "I want gluten-free desserts without nuts"
- "What can I make with chicken and rice?"
- "I need a quick breakfast idea"
- "Clear my preferences"

### Running Tests
- Entity extraction test: `python test_entity_extraction.py`
- Context retention test: `python test_context_retention.py`
- Comprehensive test: `python test_integration.py`

## API Endpoints

- Chat: `POST http://localhost:8000/chat`
  ```json
  {
    "message": "Show me vegetarian pasta recipes",
    "sender_id": "user123"
  }
  ```

- Clear preferences: `POST http://localhost:8000/clear_preferences`
  ```json
  {
    "sender_id": "user123"
  }
  ```

- Get recipes: `GET http://localhost:8000/recipes?diet=vegetarian&cuisine=Italian` 