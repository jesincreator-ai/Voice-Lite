# Custom voice dataset folders

This folder intentionally contains no recorded voices or private speaker data.

Create a language folder only after receiving explicit permission from the speaker for recording, model training and the planned use/distribution:

```text
training/data/ta/
  speaker_consent.txt
  metadata.csv
  wavs/
    000001.wav
```

`metadata.csv` format (UTF-8):

```text
000001.wav|Exact words spoken in this recording
```

Keep private signed consent forms, names, phone numbers and contact details outside Git. The validator requires a short consent statement or reference in `speaker_consent.txt`, and checks that each WAV exists and uses mono PCM16. It cannot verify the authenticity or legal sufficiency of consent.

Run the validator from the project root:

```powershell
python -m training.validate_dataset training/data/ta --language ta
```

Repeat for `si` and `en` as needed. Dataset validation is not model training.
