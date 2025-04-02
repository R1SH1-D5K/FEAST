import logging
import os
from typing import Any, Dict, List, Text, Optional
from rasa.nlu.components import Component
from rasa.nlu.config import RasaNLUModelConfig
from rasa.shared.nlu.training_data.message import Message
from rasa.shared.nlu.training_data.training_data import TrainingData
import difflib
import re

logger = logging.getLogger(__name__)

class SpellCheckerComponent(Component):
    """A custom component for spell checking in Rasa NLU pipeline."""

    name = "SpellCheckerComponent"
    provides = []
    requires = ["text"]
    defaults = {"dictionary_path": None, "confidence_threshold": 0.8, "common_food_terms_path": None}
    language_list = ["en"]

    def __init__(self, component_config: Dict[Text, Any] = None) -> None:
        super().__init__(component_config)
        self.dictionary = set()
        self.food_terms = set()
        self.confidence_threshold = self.component_config.get("confidence_threshold", 0.8)
        
        # Load main dictionary if provided
        dictionary_path = self.component_config.get("dictionary_path")
        if dictionary_path and os.path.exists(dictionary_path):
            with open(dictionary_path, "r", encoding="utf-8") as f:
                self.dictionary = set(line.strip().lower() for line in f if line.strip())
            logger.info(f"Loaded {len(self.dictionary)} words into spell checker dictionary")
        else:
            logger.warning("No dictionary provided for spell checker or file not found")
        
        # Load food-specific terms
        food_terms_path = self.component_config.get("common_food_terms_path")
        if food_terms_path and os.path.exists(food_terms_path):
            with open(food_terms_path, "r", encoding="utf-8") as f:
                self.food_terms = set(line.strip().lower() for line in f if line.strip())
            logger.info(f"Loaded {len(self.food_terms)} food terms into spell checker")
            # Add food terms to main dictionary
            self.dictionary.update(self.food_terms)

    def train(
        self, training_data: TrainingData, config: RasaNLUModelConfig, **kwargs: Any
    ) -> None:
        """Extract words from training data to build dictionary."""
        for example in training_data.training_examples:
            text = example.get("text", "")
            if text:
                words = text.lower().split()
                self.dictionary.update(words)
        
        # Extract entity values from training data
        for example in training_data.entity_examples:
            for entity in example.get("entities", []):
                value = entity.get("value", "").lower()
                if value:
                    self.dictionary.add(value)
                    # Add multi-word terms
                    if " " in value:
                        self.dictionary.update(value.split())
        
        logger.info(f"Extracted {len(self.dictionary)} words from training data for spell checking")
        
        # Save dictionary for future use
        dictionary_path = self.component_config.get("dictionary_path")
        if dictionary_path:
            os.makedirs(os.path.dirname(dictionary_path), exist_ok=True)
            with open(dictionary_path, "w", encoding="utf-8") as f:
                for word in sorted(self.dictionary):
                    f.write(f"{word}\n")
            logger.info(f"Saved dictionary to {dictionary_path}")

    def process(self, message: Message, **kwargs: Any) -> None:
        """Correct spelling in the message text."""
        if not self.dictionary:
            return
        
        text = message.get("text", "")
        if not text:
            return
        
        # Special handling for food-related terms
        # First, try to preserve known food terms before word-by-word correction
        preserved_terms = []
        for term in self.food_terms:
            if " " in term:  # Multi-word terms
                if term.lower() in text.lower():
                    preserved_terms.append(term)
        
        # Replace preserved terms with placeholders
        placeholder_map = {}
        preserved_text = text
        for i, term in enumerate(preserved_terms):
            placeholder = f"FOODTERM{i}"
            placeholder_map[placeholder] = term
            # Case-insensitive replacement
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            preserved_text = pattern.sub(placeholder, preserved_text)
        
        # Process word by word for the rest
        words = preserved_text.split()
        corrected_words = []
        
        for word in words:
            # Skip placeholders
            if word in placeholder_map:
                corrected_words.append(word)
                continue
                
            # Skip short words, punctuation, and numbers
            if len(word) <= 2 or word.isdigit() or not any(c.isalpha() for c in word):
                corrected_words.append(word)
                continue
            
            # Remove punctuation for checking
            clean_word = ''.join(c for c in word if c.isalpha())
            
            # Check if word is in dictionary
            if clean_word.lower() in self.dictionary:
                corrected_words.append(word)
                continue
            
            # Find closest match
            matches = difflib.get_close_matches(
                clean_word.lower(), 
                self.dictionary, 
                n=1, 
                cutoff=self.confidence_threshold
            )
            
            if matches:
                # Preserve original capitalization and punctuation
                corrected = matches[0]
                
                # Preserve original case pattern
                if clean_word.isupper():
                    corrected = corrected.upper()
                elif clean_word[0].isupper():
                    corrected = corrected.capitalize()
                
                # Preserve punctuation
                for i, char in enumerate(word):
                    if not char.isalpha():
                        # Insert punctuation at same position if possible
                        if i < len(corrected):
                            corrected = corrected[:i] + char + corrected[i:]
                        else:
                            corrected = corrected + char
                
                logger.debug(f"Corrected '{word}' to '{corrected}'")
                corrected_words.append(corrected)
            else:
                corrected_words.append(word)
        
        corrected_text = " ".join(corrected_words)
        
        # Restore preserved terms
        for placeholder, term in placeholder_map.items():
            corrected_text = corrected_text.replace(placeholder, term)
        
        if corrected_text != text:
            logger.info(f"Corrected text: '{text}' -> '{corrected_text}'")
            message.set("text", corrected_text, add_to_output=True) 