# Recipe Chatbot

A conversational AI chatbot that helps users find recipes based on their preferences, dietary restrictions, and available ingredients.

## Features

- **Natural Language Understanding**: Understands user queries about recipes, ingredients, cuisines, and dietary preferences
- **Context Retention**: Maintains conversation context to build up recipe preferences over multiple messages
- **Recipe Search**: Searches a database of recipes based on multiple criteria
- **Fallback Mechanisms**: Provides meaningful suggestions when no exact match is found
- **API Integration**: Offers a REST API for frontend integration

## Setup

### Prerequisites

- Python 3.8+
- MongoDB (optional, falls back to sample recipes if not available)
- Rasa 3.6.2

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

1. Start the action server:
   ```
   rasa run actions
   ```

2. In a new terminal, start the Rasa server:
   ```
   rasa run --enable-api --cors "*"
   ```

3. In a new terminal, start the API server:
   ```
   python api.py
   ```

4. Alternatively, use the provided batch script (Windows):
   ```
   run_chatbot.bat
   ```

## Testing

### Entity Extraction Testing

Test the accuracy of entity extraction: 