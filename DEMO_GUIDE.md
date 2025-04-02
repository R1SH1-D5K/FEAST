# Recipe Chatbot Demo Guide

## Setup (Before the Demo)

1. Open three terminal windows
2. In terminal 1, run: `rasa run actions`
3. In terminal 2, run: `python api.py`
4. In terminal 3, have `python demo_script.py --interactive` ready to run

## Demo Flow

### 1. Introduction (2 minutes)
- Explain the purpose of the chatbot: helping users find recipes based on preferences
- Highlight key features:
  - Natural language understanding
  - Context retention
  - Complex query handling
  - Fallback mechanisms

### 2. Interactive Demo (5 minutes)
- Run `python demo_script.py --interactive` in terminal 3
- Choose demo scenarios to showcase:
  - Basic Recipe Search
  - Complex Query Handling
  - Conversation Context
  - Edge Cases

### 3. Technical Overview (3 minutes)
- Explain the architecture:
  - NLU component (entity extraction)
  - Database integration
  - Context management
  - API for frontend integration

### 4. Q&A (5 minutes)
- Be prepared to answer questions about:
  - How entity extraction works
  - How context is maintained
  - How the database is queried
  - How the system handles edge cases

## Demo Scenarios Quick Reference

### Basic Recipe Search
- "I'm looking for vegetarian Italian recipes"
- "Do you have any pasta dishes?"

### Complex Query Handling
- "I need quick gluten-free breakfast ideas without eggs"
- "Do you have anything with fruit?"

### Conversation Context
- "Show me some Mexican recipes"
- "I want something spicy"
- "Without onions please"

### Edge Cases
- "I don't eat dairy"
- "Show me recipes ready in under 30 minutes"

### Minimal Ingredient Recipes
- "What can I cook with just rice and tomatoes?"

### Dietary Restrictions
- "I'm allergic to nuts, what can I make?"
- "I also need gluten-free options"

## Troubleshooting

If the chatbot doesn't respond as expected:
1. Check that all services are running
2. Try clearing preferences: "Clear my preferences"
3. Try a simpler query to reset the conversation
4. Have the fallback demo ready: "python demo_script.py" (non-interactive) 