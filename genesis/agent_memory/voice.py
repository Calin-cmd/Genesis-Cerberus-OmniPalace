"""
Genesis v5.6.9 — Simple Text-to-Speech output using speakers.
Low dependency, Windows-first.
"""

import sys
from pathlib import Path

try:
    # Windows built-in (no extra install)
    import win32com.client
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

try:
    # Optional nicer voice (pip install pyttsx3 if wanted)
    import pyttsx3
    HAS_PYTTX = True
except ImportError:
    HAS_PYTTX = False


class VoiceInterface:
    """Simple TTS output."""

    @staticmethod
    def speak(text: str, rate: int = 180):
        """Speak text using available engine."""
        if not text or len(text.strip()) < 3:
            return

        clean_text = text[:500]  # Limit length for natural speech

        # Try Windows built-in first (no install needed)
        if HAS_WIN32:
            try:
                speaker = win32com.client.Dispatch("SAPI.SpVoice")
                speaker.Rate = rate - 200  # SAPI rate is different
                speaker.Speak(clean_text)
                return
            except:
                pass

        # Fallback to pyttsx3 if installed
        if HAS_PYTTX:
            try:
                engine = pyttsx3.init()
                engine.setProperty('rate', rate)
                engine.say(clean_text)
                engine.runAndWait()
                return
            except:
                pass

        # Ultimate fallback: print only
        print(f"[SPEAK] {clean_text}")


# Optional: Add to tools.py later for /speak command