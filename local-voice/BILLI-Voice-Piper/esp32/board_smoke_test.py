"""Run real clip playback checks on a BILLI ESP32 after wiring the I2S TX.

Call run(voice) after creating VoiceLite with your already-configured I2S TX
object and mounting the SD card. This script deliberately assigns no GPIOs.
"""

import time


def run(voice, languages=("ta", "si"), modes=("standard", "rugged"),
        clips=("hello", "ready"), delay_ms=10):
    results = []
    for language in languages:
        for mode in modes:
            voice.stop()
            voice.set_language(language)
            voice.set_mode(mode)
            for clip_id in clips:
                started = voice.speak_clip(clip_id)
                if not started:
                    result = {"language": language, "mode": mode, "clip": clip_id,
                              "started": False, "ok": False, "error": voice.last_error}
                    print("FAIL", result)
                    results.append(result)
                    continue
                while voice.state == "speaking":
                    voice.tick()
                    sleep_ms = getattr(time, "sleep_ms", None)
                    if callable(sleep_ms):
                        sleep_ms(delay_ms)
                    else:
                        time.sleep(delay_ms / 1000.0)
                result = {"language": language, "mode": mode, "clip": clip_id,
                          "started": True, "ok": bool(voice.last_output),
                          "error": voice.last_error}
                print("PASS" if result["ok"] else "FAIL", result)
                results.append(result)
    return results
