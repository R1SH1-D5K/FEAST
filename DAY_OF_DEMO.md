# Day of Demo Checklist

## Before the Demo (1 hour before)

- [ ] Ensure your development environment is ready
- [ ] Run `python pre_demo_checklist.py` to verify all components
- [ ] Run `rasa train --force` to ensure the model is up-to-date
- [ ] Test the demo script: `python demo_script.py --interactive`
- [ ] Prepare three terminal windows:
  - Terminal 1: For running the action server
  - Terminal 2: For running the API server
  - Terminal 3: For running the demo script

## Starting the Demo (5 minutes before)

- [ ] In Terminal 1: Run `rasa run actions`
- [ ] In Terminal 2: Run `python api.py`
- [ ] In Terminal 3: Have `python demo_script.py --interactive` ready to run
- [ ] Have the DEMO_GUIDE.md open for reference
- [ ] Have a browser open to the README.md for any additional reference

## During the Demo

- [ ] Start with a brief introduction to the chatbot
- [ ] Run the interactive demo
- [ ] Showcase at least 3 different scenarios
- [ ] Highlight how context is maintained
- [ ] Show how complex queries are handled
- [ ] Demonstrate fallback mechanisms

## After the Demo

- [ ] Answer any questions about the implementation
- [ ] Offer to show specific components if requested
- [ ] Provide the QUICK_START.md guide for reviewers who want to try it themselves 