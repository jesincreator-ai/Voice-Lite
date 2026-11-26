# Training or fine-tuning a custom BILLI voice

## Important distinction

The current repository uses pretrained Piper voices and two synthesis profiles. It does **not** train a new male speaker. The Standard/Rugged variants are generated from the same language voice model with different inference settings.

To create two truly different male identities, collect a separate, consented recording dataset for each target speaker and language. To create one speaker with separate Standard/Rugged speaking styles, record both styles consistently and plan whether to train separate checkpoints or use a single model with inference profiles. Do not describe a profile change as training.

## Dataset layout

For one speaker in one language:

```text
training/data/ta/
  speaker_consent.txt
  metadata.csv
  wavs/
    000001.wav
    000002.wav
```

`metadata.csv` is UTF-8 and uses one `filename.wav|Exact spoken transcript` row per recording. Use the actual spoken words, not a translated prompt if the recording differs.

The speaker must explicitly agree to recording, model training and the intended use/distribution. Keep their name, contact details or signed private documents outside the repository. Store a short consent statement or private consent-record reference in `speaker_consent.txt`; do not publish personal information.

## Recording quality

- One speaker per dataset.
- Quiet room, same microphone position and input gain.
- No music, echo, clipping, compression artifacts or synthetic background noise.
- Natural pace and consistent pronunciation.
- Exact UTF-8 transcript for every WAV.
- Remove duplicate, empty, clipped or badly aligned clips before training.
- Use fluent Tamil/Sinhala reviewers to correct spelling, script and spoken phrasing.

The dataset validator checks file safety, transcript presence, consent-file presence, mono PCM16 WAVs and valid sample-rate ranges. It does not judge pronunciation quality, speaker identity, consent authenticity or dataset sufficiency.

## Validate a dataset

```powershell
python -m training.validate_dataset training/data/ta --language ta
python -m training.validate_dataset training/data/si --language si
```

A valid result is only a format/metadata gate, not proof that the dataset is good enough to train a useful model.

## Piper training toolchain

Piper training uses a separate training environment, PyTorch Lightning and compiled alignment components. It is much heavier than the small ESP32 playback firmware and should be run on a PC/workstation, not on the original ESP32. Follow the upstream guide for exact OS dependencies and training flags:

https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/TRAINING.md

The upstream guide uses `python -m piper.train fit`, a metadata CSV with `|` delimiter, a WAV directory, a language phonemizer, a cache directory, a config output path and optionally a compatible pretrained checkpoint. Install the training extra from a clone of the Piper project, not into the ESP32 firmware:

```bash
git clone https://github.com/OHF-Voice/piper1-gpl.git
cd piper1-gpl
python -m venv .venv
python -m pip install -e '.[train]'
./build_monotonic_align.sh
```

Then use the command template from the upstream training guide, replacing the CSV path, audio directory, voice name, sample rate, eSpeak voice and checkpoint with values that match the selected language and model. Do not reuse a Tamil checkpoint/config for Sinhala or vice versa unless the upstream training procedure explicitly supports that language transfer and the result has been evaluated by native speakers.

## Export and evaluate

After training, export the model to a Piper-compatible `.onnx` plus matching `.onnx.json` configuration using the current upstream Piper workflow. Test it on the PC with held-out transcripts first. A fluent speaker should rate pronunciation, word correctness, intelligibility, voice identity consistency and both operating modes.

A custom trained voice model does not run on the ESP32 in this design. Exported model inference remains on the PC; the ESP32 only receives PCM WAV clips. If you need the robot to speak unrestricted text without PC preparation, you would need a different hardware architecture with substantially more compute/memory or an external TTS service, which is outside the original ESP32-WROOM-only goal.
