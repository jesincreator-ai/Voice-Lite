# PC-side Tamil/Sinhala voice clip generator

This tool runs Piper TTS on a Windows/Linux/macOS PC. It downloads the small voice-model files once, generates BILLI's phrase set, and converts every file to the exact format accepted by the ESP32 MicroPython player. The ESP32 does not load ONNX models or run neural TTS.

## Windows quick start

Install Python 3.10 or newer and open PowerShell in the Voice-Lite repository folder:

\`\`\`powershell
py -m pip install --upgrade pip
py -m pip install piper-tts
py tools/generate_voice_clips.py --languages all
\`\`\`

The first run downloads two model/config pairs from Hugging Face (roughly 130 MB total). Piper synthesizes six Tamil and six Sinhala phrases into:

\`\`\`text
voice_clips/generated/ta/hello.wav
voice_clips/generated/ta/ready.wav
...
voice_clips/generated/si/hello.wav
voice_clips/generated/si/ready.wav
...
\`\`\`

Copy the \`ta\` and \`si\` directories into \`billi_voice\` at the root of the SD card, so the final paths are \`/billi_voice/ta/hello.wav\` etc. With the card mounted at \`/sd\`, the firmware opens \`/sd/billi_voice/ta/hello.wav\` and \`/sd/billi_voice/si/hello.wav\`.

To generate only one language, use \`--languages ta\` or \`--languages si\`. Use \`--force\` to replace existing files. By default, an existing clip is preserved. After both the models and clips have been downloaded/generated, no internet connection is needed by BILLI.

## Voice models and licences

- Tamil: \`tinisoft/piper-ta_IN-rasa_female-medium\`, CC BY 4.0. Attribution: AI4Bharat Rasa dataset; Varadhan et al., Interspeech 2024.
- Sinhala: \`unicef/piper-si_LK-ashoka-medium\`, MIT.

Model files stay on the PC in \`tools/models/piper/\`; they must not be copied to the ESP32. Only generated WAV clips go onto the SD card. Check the model cards for current model terms and attribution before redistributing audio or model files.

## Troubleshooting

- \`piper\` not found: run \`py -m pip install piper-tts\`, then reopen PowerShell.
- Model download failure: check internet access and rerun the command; partial \`.part\` files are removed automatically.
- Missing model/config in offline mode: put both the \`.onnx\` and matching \`.onnx.json\` in \`tools/models/piper/\`, then run with \`--offline-models\`.
- If Piper reports a phonemizer/eSpeak error, install the eSpeak NG runtime for your operating system and retry. Do not install TTS packages on the ESP32.
- A WAV that is not 16 kHz mono PCM16 will be rejected by \`SDWavSpeaker\`; this tool converts and checks the output for that player format.
