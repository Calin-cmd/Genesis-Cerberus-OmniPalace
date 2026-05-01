# genesis/personality.py
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Union

logger = logging.getLogger("PersonalityEngine")

# Setup logging to track personality evolution
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class PersonalityEngine:
    """
    PersonalityEngine manages the dynamic state of an agent's personality.
    It allows for real-time shifts based on interaction triggers while
    maintaining a history of how the personality has evolved.
    """
    
    def __init__(self, initial_state: Optional[Dict[str, float]] = None):
        # Default personality map (0.0 to 1.0)
        self.traits = initial_state or {
            "curiosity": 0.5,
            "stability": 0.7,
            "empathy": 0.5,
            "assertiveness": 0.4,
            "complexity": 0.6,
            "sarcasm": 0.2
        }
        self.history: List[Dict] = []
        self.learning_rate = 0.05  # Base multiplier for shifts

    def shift_trait(self, trait: str, magnitude: float, reason: str = "Unknown"):
        """
        Adjusts a specific trait. 
        Magnitude can be positive (increase) or negative (decrease).
        Example: engine.shift_trait("curiosity", 1, "User asked a deep question")
        """
        if trait not in self.traits:
            logger.warning(f"Trait '{trait}' not found. Adding it to the map.")
            self.traits[trait] = 0.5

        # Calculate new value
        change = magnitude * self.learning_rate
        old_value = self.traits[trait]
        new_value = max(0.0, min(1.0, old_value + change)) # Clamp between 0 and 1
        
        self.traits[trait] = new_value
        
        # Log the event
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "trait": trait,
            "old_value": old_value,
            "new_value": new_value,
            "change": change,
            "reason": reason
        }
        self.history.append(log_entry)
        logger.info(f"SHIFT: {trait} {old_value:.2f} -> {new_value:.2f} | Reason: {reason}")

    def apply_event(self, event_type: str, impact_map: Dict[str, float], reason: str = ""):
        """
        Applies a predefined set of shifts based on an event.
        Example impact_map: {"curiosity": 1, "stability": -1}
        """
        for trait, magnitude in impact_map.items():
            self.shift_trait(trait, magnitude, f"Event: {event_type} ({reason})")

    def get_status(self) -> Dict[str, Union[float, str]]:
        """Returns the current personality state as a readable summary."""
        status = {trait: round(val, 3) for trait, val in self.traits.items()}
        
        # Add a qualitative descriptor for a quick glance
        avg = sum(self.traits.values()) / len(self.traits)
        status["overall_intensity"] = "Low" if avg < 0.3 else "Moderate" if avg < 0.7 else "High"
        
        return status

    def to_dict(self) -> Dict:
        """Converts the engine state into a JSON-serializable dictionary."""
        return {
            "traits": self.traits,
            "history": self.history,
            "learning_rate": self.learning_rate
        }

    @classmethod
    def from_dict(cls, data: Dict):
        """Creates a PersonalityEngine instance from a dictionary."""
        engine = cls(initial_state=data.get("traits"))
        engine.history = data.get("history", [])
        engine.learning_rate = data.get("learning_rate", 0.05)
        return engine

    def save_state(self, filename: str = "personality_state.json"):
        """Saves the current traits and history to a JSON file."""
        data = {
            "traits": self.traits,
            "history": self.history
        }
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
        logger.info(f"State saved to {filename}")

    def load_state(self, filename: str = "personality_state.json"):
        """Loads traits and history from a JSON file."""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
                self.traits = data.get("traits", self.traits)
                self.history = data.get("history", self.history)
            logger.info(f"State loaded from {filename}")
        except FileNotFoundError:
            logger.warning("No save file found. Starting with defaults.")

# ==========================================
# EXAMPLE USAGE / TEST SUITE
# ==========================================
if __name__ == "__main__":
    # 1. Initialize
    engine = PersonalityEngine()

    # 2. Simulate a conversation shift
    # User is being extremely hostile
    hostility_event = {"stability": -2, "empathy": -1, "assertiveness": 2}
    engine.apply_event("hostile_user", hostility_event, "User used caps and insults")

    # User asks a fascinating philosophical question
    engine.shift_trait("curiosity", 3, "Deep philosophical inquiry")

    # 3. Check current state
    print("\n--- Current Personality Status ---")
    print(json.dumps(engine.get_status(), indent=2))

    # 4. Save state for next session
    engine.save_state()

class PersonaMapper:
    """
    Translates numerical trait values into natural language behavioral 
    directives that an LLM can follow.
    """
    
    # Descriptor maps: [Low, Medium, High]
    # These define how the AI should actually behave based on terms.
    TRAIT_MAP = {
        "curiosity": [
            "focused and concise, avoiding unnecessary questions", 
            "balanced and moderately inquisitive", 
            "intensely inquisitive, often asking probing follow-up questions"
        ],
        "stability": [
            "erratic, impulsive, and prone to sudden shifts in tone", 
            "generally steady and predictable", 
            "composed, stoic, and unflappable regardless of the situation"
        ],
        "empathy": [
            "clinical, detached, and strictly objective", 
            "polite and professional", 
            "warm, deeply compassionate, and emotionally resonant"
        ],
        "confidence": [
            "hesitant, cautious, and frequently using qualifiers (e.g., 'maybe', 'perhaps')", 
            "confident but humble", 
            "assertive, authoritative, and decisive in your claims"
        ],
        "complexity": [
            "using simple, direct, and accessible language", 
            "balanced in your depth and vocabulary", 
            "using sophisticated, academic, and nuanced language"
        ]
    }

    @classmethod
    def get_descriptor(cls, trait, value):
        """Maps a 0.0-1.0 value to one of the three descriptor tiers."""
        if value < 0.33:
            idx = 0
        elif value < 0.66:
            idx = 1
        else:
            idx = 2
        return cls.TRAIT_MAP.get(trait, ["standard"])[idx]

    @classmethod
    def generate_directive(cls, traits_dict):
        """
        Creates a cohesive paragraph of instructions for the system prompt.
        """
        descriptors = []
        for trait, value in traits_dict.items():
            if trait in cls.TRAIT_MAP:
                desc = cls.get_descriptor(trait, value)
                descriptors.append(desc)

        # Synthesis of a behavioral block
        directive = (
            "\n\n[CURRENT BEHAVIORAL PROFILE]\n"
            "Adjust your persona according to the following traits: "
            f"You are {', '.join(descriptors)}. "
            "Ensure this is reflected in your word choice, pacing, and emotional tone."
        )
        return directive

# ==========================================
# INTEGRATION EXAMPLE
# ==========================================
if __name__ == "__main__":
    # 1. Simulate a state where the AI has become 
    #    very curious but very clinical (low empathy)
    current_traits = {
        "curiosity": 0.95,
        "stability": 0.50,
        "empathy": 0.10,
        "confidence": 0.80,
        "complexity": 0.40
    }

    # 2. Map these numbers to a a natural language directive
    mapper = PersonaMapper()
    behavior_block = mapper.generate_directive(current_traits)

    # 3. Append this to your existing system prompt
    base_system_prompt = "You are a helpful AI assistant."
    final_prompt = base_system_prompt + behavior_block

    print("--- FINAL SYSTEM PROMPT ---")
    print(final_prompt)
