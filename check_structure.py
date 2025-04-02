import os
import sys

# Print current directory
print(f"Current directory: {os.getcwd()}")

# Print Python path
print(f"Python path: {sys.path}")

# List files in current directory
print("Files in current directory:")
for item in os.listdir('.'):
    print(f"  - {item}")

# Check if actions.py exists
actions_py = os.path.join(os.getcwd(), "actions.py")
print(f"actions.py exists: {os.path.exists(actions_py)}")

# Check if actions directory exists
actions_dir = os.path.join(os.getcwd(), "actions")
print(f"actions directory exists: {os.path.exists(actions_dir)}")

# If actions directory exists, list its contents
if os.path.exists(actions_dir):
    print("Contents of actions directory:")
    for item in os.listdir(actions_dir):
        print(f"  - {item}") 