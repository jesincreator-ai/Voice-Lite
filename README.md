# Voice Lite

A lightweight browser voice module for BILLI R-20 using native Web Speech APIs, with graceful feature detection and no cloud dependency.


## ESP32-WROOM MicroPython manager
`voice_lite.py` provides a lightweight manager for language/state and callback-based input/output. The WROOM has no onboard audio codec: microphone and speaker adapters must be wired and implemented for your modules. Mobile browser demo: `mobile_test.html`, using native Web Speech APIs if available.
