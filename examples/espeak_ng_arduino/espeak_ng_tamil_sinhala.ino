/*
 * BILLI R-20 experimental Tamil/Sinhala dynamic TTS test.
 *
 * Arduino C++ only. This file is not a MicroPython module and is not
 * integrated with voice_lite.py. Define the actual BILLI I2S pins below
 * from the confirmed wiring map before compiling.
 *
 * Dependencies:
 *   - arduino-espeak-ng
 *   - arduino-posix-fs
 *   - arduino-audio-tools
 */

#include <AudioTools.h>
#include <FileSystems.h>
#include <espeak.h>

#ifndef BILLI_I2S_BCLK_PIN
#error "Define BILLI_I2S_BCLK_PIN from the confirmed BILLI wiring map."
#endif
#ifndef BILLI_I2S_LRCLK_PIN
#error "Define BILLI_I2S_LRCLK_PIN from the confirmed BILLI wiring map."
#endif
#ifndef BILLI_I2S_DOUT_PIN
#error "Define BILLI_I2S_DOUT_PIN from the confirmed BILLI wiring map."
#endif

I2SStream i2s;
ESpeak espeak(i2s, true);  // Keep the upstream English default too.

static bool selectVoice(const String &language) {
  if (language == "ta") {
    return espeak.setVoice("ta");
  }
  if (language == "si") {
    return espeak.setVoice("si");
  }
  if (language == "en") {
    return espeak.setVoice("en");
  }
  return false;
}

static void setVoiceMode(const String &mode) {
  if (mode == "rugged") {
    espeak.setRate(135);  // Words per minute.
    espeak.setPitch(42);  // eSpeak pitch range is 0..100.
  } else {
    espeak.setRate(165);
    espeak.setPitch(55);
  }
}

static void handleLine(String line) {
  line.trim();
  const int first = line.indexOf('|');
  const int second = first < 0 ? -1 : line.indexOf('|', first + 1);
  if (first <= 0 || second <= first + 1 || second >= (int)line.length() - 1) {
    Serial.println("Use: language|standard-or-rugged|text");
    return;
  }

  const String language = line.substring(0, first);
  const String mode = line.substring(first + 1, second);
  const String text = line.substring(second + 1);
  if (mode != "standard" && mode != "rugged") {
    Serial.println("ERROR: mode must be standard or rugged.");
    return;
  }

  if (text.length() > 384) {
    Serial.println("ERROR: test text exceeds 384 UTF-8 bytes.");
    return;
  }
  if (!selectVoice(language)) {
    Serial.println("ERROR: eSpeak language voice could not be selected.");
    return;
  }

  setVoiceMode(mode);
  Serial.print("TTS ");
  Serial.print(language);
  Serial.print(" / ");
  Serial.print(mode);
  Serial.print(": ");
  Serial.println(text);

  if (!espeak.say(text.c_str())) {
    Serial.println("ERROR: eSpeak synthesis failed.");
  } else {
    Serial.println("TTS request completed.");
  }
}

void setup() {
  Serial.begin(115200);
  Serial.setTimeout(10000);
  delay(250);

  // The base ESpeak object registers English when begin() runs. Add Tamil
  // and Sinhala PROGMEM dictionaries and language rules before begin().
  espeak.add("/mem/data/ta_dict",
             espeak_ng_data_ta_dict,
             espeak_ng_data_ta_dict_len);
  espeak.add("/mem/data/lang/ta",
             espeak_ng_data_lang_dra_ta,
             espeak_ng_data_lang_dra_ta_len);

  espeak.add("/mem/data/si_dict",
             espeak_ng_data_si_dict,
             espeak_ng_data_si_dict_len);
  espeak.add("/mem/data/lang/si",
             espeak_ng_data_lang_inc_si,
             espeak_ng_data_lang_inc_si_len);

  espeak.setFlags(espeakCHARS_UTF8);
  if (!espeak.begin()) {
    Serial.println("FATAL: eSpeak initialization failed.");
    while (true) {
      delay(1000);
    }
  }

  const audio_info info = espeak.audioInfo();
  auto config = i2s.defaultConfig(TX_MODE);
  config.channels = info.channels;
  config.sample_rate = info.sample_rate;
  config.bits_per_sample = info.bits_per_sample;

  config.pin_bck = BILLI_I2S_BCLK_PIN;
  config.pin_ws = BILLI_I2S_LRCLK_PIN;
  config.pin_data = BILLI_I2S_DOUT_PIN;

  if (!i2s.begin(config)) {
    Serial.println("FATAL: I2S output initialization failed.");
    while (true) {
      delay(1000);
    }
  }

  Serial.println("BILLI eSpeak NG experimental TTS ready.");
  Serial.println("Send UTF-8 lines: ta|standard|text or si|rugged|text");
}

void loop() {
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    handleLine(line);
  }
}
