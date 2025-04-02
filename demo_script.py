import asyncio
import logging
import argparse
import json
import os
import sys
import uuid
from rasa.core.agent import Agent
import colorama
from colorama import Fore, Style

# Initialize colorama
colorama.init()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Demo scenarios
DEMO_SCENARIOS = [
    {
        "name": "Basic Recipe Search",
        "description": "Demonstrate basic recipe search functionality",
        "steps": [
            "Show me vegetarian recipes",
            "I prefer Italian cuisine",
            "I want something with pasta"
        ]
    },
    {
        "name": "Complex Query Handling",
        "description": "Demonstrate handling of complex, multi-constraint queries",
        "steps": [
            "I need a quick gluten-free breakfast without eggs",
            "Show me spicy vegetarian Mexican dishes ready in under 30 minutes"
        ]
    },
    {
        "name": "Context Retention",
        "description": "Demonstrate how the chatbot maintains context across messages",
        "steps": [
            "I want vegetarian recipes",
            "Show me Italian options",
            "I prefer pasta dishes",
            "Actually, make it vegan instead"
        ]
    },
    {
        "name": "Ingredient-Based Search",
        "description": "Demonstrate searching based on available ingredients",
        "steps": [
            "What can I make with chicken, rice, and bell peppers?",
            "I also have tomatoes and onions"
        ]
    },
    {
        "name": "Preference Management",
        "description": "Demonstrate preference management and summarization",
        "steps": [
            "I want vegetarian Italian recipes",
            "Summarize my preferences",
            "Clear my preferences",
            "What are my current preferences?"
        ]
    },
    {
        "name": "Error Recovery",
        "description": "Demonstrate graceful handling of errors and edge cases",
        "steps": [
            "I want a recipe with unicorn meat",
            "Show me recipes that are both vegan and contain beef",
            "What's the weather like today?"
        ]
    }
]

class RecipeChatbotDemo:
    def __init__(self):
        self.agent = None
        self.sender_id = f"demo_user_{uuid.uuid4()}"
    
    async def load_agent(self):
        """Load the Rasa agent"""
        logger.info("Loading Rasa agent...")
        
        # Find the latest model
        models_dir = "./models"
        model_files = [f for f in os.listdir(models_dir) if f.endswith('.tar.gz')]
        if not model_files:
            logger.error("No model found in models directory")
            return False
        
        latest_model = os.path.join(models_dir, sorted(model_files)[-1])
        logger.info(f"Using model: {latest_model}")
        
        # Load the agent
        self.agent = await Agent.load(latest_model)
        logger.info("Agent loaded successfully")
        return True
    
    async def process_message(self, message):
        """Process a user message and return the response"""
        if not self.agent:
            return ["Agent not loaded. Please load the agent first."]
        
        response = await self.agent.handle_text(message, sender_id=self.sender_id)
        return [msg.get("text", "") for msg in response if msg.get("text")]
    
    async def run_scenario(self, scenario):
        """Run a demo scenario"""
        print(f"\n{Fore.CYAN}=== Scenario: {scenario['name']} ==={Style.RESET_ALL}")
        print(f"{Fore.CYAN}Description: {scenario['description']}{Style.RESET_ALL}\n")
        
        for i, step in enumerate(scenario["steps"]):
            print(f"\n{Fore.GREEN}User ({i+1}/{len(scenario['steps'])}): {step}{Style.RESET_ALL}")
            
            # Process the message
            responses = await self.process_message(step)
            
            # Print bot responses
            for response in responses:
                print(f"{Fore.YELLOW}Bot: {response}{Style.RESET_ALL}")
            
            # Pause between steps
            if i < len(scenario["steps"]) - 1:
                input(f"{Fore.CYAN}Press Enter to continue...{Style.RESET_ALL}")
        
        print(f"\n{Fore.CYAN}=== End of Scenario: {scenario['name']} ==={Style.RESET_ALL}")
    
    async def run_interactive(self):
        """Run in interactive mode"""
        print(f"\n{Fore.CYAN}=== Interactive Recipe Chatbot Demo ==={Style.RESET_ALL}")
        print(f"{Fore.CYAN}Type 'exit' to quit, 'clear' to clear preferences{Style.RESET_ALL}\n")
        
        while True:
            # Get user input
            user_input = input(f"{Fore.GREEN}You: {Style.RESET_ALL}")
            
            # Check for exit command
            if user_input.lower() == "exit":
                print(f"{Fore.CYAN}Exiting demo...{Style.RESET_ALL}")
                break
            
            # Check for clear command
            if user_input.lower() == "clear":
                await self.process_message("clear preferences")
                print(f"{Fore.YELLOW}Bot: I've cleared all your preferences.{Style.RESET_ALL}")
                continue
            
            # Process the message
            responses = await self.process_message(user_input)
            
            # Print bot responses
            for response in responses:
                print(f"{Fore.YELLOW}Bot: {response}{Style.RESET_ALL}")
    
    async def run_all_scenarios(self):
        """Run all demo scenarios"""
        for scenario in DEMO_SCENARIOS:
            await self.run_scenario(scenario)
            input(f"{Fore.CYAN}Press Enter to continue to the next scenario...{Style.RESET_ALL}")

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Recipe Chatbot Demo")
    parser.add_argument("--scenario", type=int, help="Run a specific scenario (1-6)")
    parser.add_argument("--interactive", action="store_true", help="Run in interactive mode")
    parser.add_argument("--all", action="store_true", help="Run all scenarios")
    args = parser.parse_args()
    
    demo = RecipeChatbotDemo()
    success = await demo.load_agent()
    
    if not success:
        logger.error("Failed to load agent. Exiting.")
        return
    
    if args.interactive:
        await demo.run_interactive()
    elif args.scenario:
        if 1 <= args.scenario <= len(DEMO_SCENARIOS):
            await demo.run_scenario(DEMO_SCENARIOS[args.scenario - 1])
        else:
            logger.error(f"Invalid scenario number. Choose between 1 and {len(DEMO_SCENARIOS)}.")
    elif args.all:
        await demo.run_all_scenarios()
    else:
        # Default to interactive mode
        await demo.run_interactive()

if __name__ == "__main__":
    asyncio.run(main()) 