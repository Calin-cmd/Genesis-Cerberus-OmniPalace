"""
Genesis v5.6.9 Cerberus OmniPalace — Voice Interface
Voice input/output using speech_recognition and pyttsx3.
Updated with Obsidian Wiki status announcements.
"""

from __future__ import annotations

from .dependencies import HAS_VOICE


# ====================== VOICE INTERFACE ======================
class VoiceInterface:
    """Voice input/output interface for Genesis with Wiki awareness."""

    @staticmethod
    def listen() -> str:
        """Listen for voice input using microphone"""
        if not HAS_VOICE:
            print("[VOICE] Voice recognition not available. Falling back to text input.")
            return input("You: ")

        try:
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            
            with sr.Microphone() as source:
                print("🎤 Listening... (speak now)")
                # Adjust for ambient noise
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = recognizer.listen(source, timeout=8, phrase_time_limit=12)

            text = recognizer.recognize_google(audio)
            print(f"🗣️  Heard: {text}")
            return text.strip()
            
        except sr.UnknownValueError:
            print("[VOICE] Could not understand audio.")
            return ""
        except sr.RequestError as e:
            print(f"[VOICE] Speech recognition service error: {e}")
            return ""
        except Exception as e:
            print(f"[VOICE] Error during listening: {e}")
            return input("You: ")

    @staticmethod
    def speak(text: str):
        """Speak text using text-to-speech with occasional Wiki status."""
        if not HAS_VOICE or not text:
            return

        try:
            import pyttsx3
            engine = pyttsx3.init()
            # Optional: configure voice properties
            engine.setProperty('rate', 165)    # speaking rate
            engine.setProperty('volume', 0.9)  # volume level
            
            # Occasionally mention Wiki status for better user awareness
            spoken_text = text[:480]
            if random.random() < 0.12 and "wiki" not in text.lower():
                spoken_text += " The Obsidian Wiki is active and self-healing."
            
            engine.say(spoken_text)
            engine.runAndWait()
        except Exception as e:
            print(f"[VOICE] Text-to-speech failed: {e}")

    @staticmethod
    def is_available() -> bool:
        """Check if voice features are available"""
        return HAS_VOICE


# Quick test function
def test_voice():
    """Simple test for voice functionality"""
    if not HAS_VOICE:
        print("Voice dependencies not installed.")
        return
    
    print("Testing voice output...")
    VoiceInterface.speak("Hello, this is Genesis testing voice output. The Obsidian Wiki is ready.")
    print("Now testing voice input...")
    heard = VoiceInterface.listen()
    print(f"You said: {heard}")