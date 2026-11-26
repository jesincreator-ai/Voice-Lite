"""Example M1/top-level wiring for the existing MicroPython manager split.

The caller supplies already-created M6, display and I2S TX objects from the
robot's hardware configuration. No GPIO numbers, servo objects or M8 bypasses
are defined here.
"""

import time
from voice_lite import VoiceLite
from esp32_wav_speaker import SDWavSpeaker
from m6_speech_bridge import M6SpeechBridge


def create_voice_runtime(i2s_tx, m6_manager, language="en", mode="standard"):
    voice = VoiceLite(language=language, mode=mode)
    voice.speaker = SDWavSpeaker(i2s_tx, root="/sd/billi_voice")
    voice.attach_speech_observer(M6SpeechBridge(m6_manager))
    if not set_operating_mode(mode, voice, m6_manager):
        raise ValueError("Could not synchronize M5/M6 operating mode")
    return voice


def set_operating_mode(mode, voice, m6_manager, now_ms=None):
    """M1 sends the same mode to M5 and M6; neither manager owns the other."""
    mode = VoiceLite.MODE_ALIASES.get(mode, mode)
    if mode not in VoiceLite.MODES:
        return False
    if now_ms is None:
        now_ms = time.ticks_ms() if hasattr(time, "ticks_ms") else int(time.time() * 1000)
    if not voice.set_mode(mode):
        return False
    if not m6_manager.set_mode(mode, now_ms):
        return False
    return True


def service_voice_and_face(voice, m6_manager, display_adapter, now_ms=None):
    """Call once from the robot's cooperative main loop (e.g. every 10–20 ms)."""
    if now_ms is None:
        now_ms = time.ticks_ms() if hasattr(time, "ticks_ms") else int(time.time() * 1000)
    frame = m6_manager.tick(now_ms)
    display_adapter.draw(frame)
    voice.tick()  # One bounded, non-blocking I2S scheduling step after rendering.


# Integration sketch (the actual top-level supervisor supplies hardware):
#
# voice = create_voice_runtime(i2s_tx, m6_manager, language="ta")
# voice.speak_clip("hello")
# while True:
#     now = time.ticks_ms()
#     service_voice_and_face(voice, m6_manager, display_adapter, now)
#     time.sleep_ms(10)
#
# Existing M7 servo updates and M8 guardian checks remain in the supervisor's
# own loop. Do not put blocking audio, file, or network operations there.
