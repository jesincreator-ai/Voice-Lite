"""Attach the local WAV voice player to BILLI's existing M5/M6 managers.

The board supervisor supplies an already-mounted SD card, I2S TX instance,
M6 manager and display. This module assigns no GPIOs and does not replace M1,
M7 or M8.
"""

from esp32.voice_lite import VoiceLite, M6SpeechBridge
from esp32.wav_player import WavPlayer


def create_voice(i2s_tx, m6_manager, language="ta", mode="standard",
                 i2s_ibuf_bytes=20000, root="/sd/billi_voice"):
    player = WavPlayer(
        i2s_tx,
        root=root,
        chunk_bytes=512,
        i2s_ibuf_bytes=i2s_ibuf_bytes,
    )
    voice = VoiceLite(player, language=language, mode=mode)
    voice.attach_speech_observer(M6SpeechBridge(m6_manager))
    if not m6_manager.set_mode(mode, _now_ms()):
        raise ValueError("M6 rejected operating mode {}".format(mode))
    return voice


def set_mode(voice, m6_manager, mode):
    if not voice.set_mode(mode):
        return False
    return bool(m6_manager.set_mode(mode, _now_ms()))


def service_voice(voice, m6_manager, display_adapter):
    """Call from the existing cooperative supervisor, around every 10 ms."""
    voice.tick()
    frame = m6_manager.tick(_now_ms())
    display_adapter.draw(frame)


def _now_ms():
    import time
    ticks_ms = getattr(time, "ticks_ms", None)
    if callable(ticks_ms):
        return ticks_ms()
    return int(time.time() * 1000)


# Existing M1/top-level supervisor example:
#
# voice = create_voice(i2s_tx, m6_manager, language="ta", mode="standard",
#                      i2s_ibuf_bytes=YOUR_I2S_IBUF_BYTES)
# voice.speak_clip("hello")
# while True:
#     service_voice(voice, m6_manager, display_adapter)
#     # Continue existing M7 controller and M8 guardian work unchanged.
