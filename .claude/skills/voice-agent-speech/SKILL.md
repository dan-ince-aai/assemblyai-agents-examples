---
name: voice-agent-speech
description: Tune how an AssemblyAI voice agent hears and speaks with the assemblyai-agents SDK - get names, spellings, codes and numbers right (keyterms, transcription mode and prompt), turn-taking and interruptions (silence thresholds, lines a caller cannot talk over), other languages, noisy or speakerphone lines, and voice choice. Use this when callers are misheard, the agent cuts people off or waits too long, the greeting gets talked over, or the user wants another language or a different voice.
---

# Hearing and speaking

All of this is `input=AudioInput(...)`, plus `voice=` on the agent. Change one
thing at a time and compare real calls before and after
(`voice-agent-call-review`): every setting here trades one failure for another.

## Names, spellings, codes and numbers

Most mishearing is a word the recogniser has never seen. Fix that before
anything else.

```python
input=AudioInput(
    keyterms=["Northwind", "Dr Okonkwo", "Invisalign", "NW-4471"],   # up to 100
    transcription_mode="max_accuracy",
    transcription_prompt="Callers read order numbers like NW-4471 and spell surnames letter by letter.",
)
```

- **`keyterms`**: brand, product, staff and street names, and the shape of
  codes. Generate the list from the business's data, not by hand.
- **`transcription_mode`**: `balanced` by default. `max_accuracy` for lines
  that are mostly identifiers; `min_latency` when speed matters more than
  spelling.
- **`transcription_prompt`** (up to 1750 characters): what callers will say
  and how. It steers formatting as well as words.
- **In code, not in the model:** normalise digits with `digits_said()`, accept
  "for" as 4 and "oh" as 0, and read every identifier back before using it.
  For a surname, ask the caller to spell it, and confirm it back letter by
  letter.

## Turn-taking

```python
input=AudioInput(
    uninterruptible_turns=["greeting"],
    extra={"turn_detection": {"min_silence": 700, "max_silence": 2500}},
)
```

- **Cutting people off** while they think, or while they read a long number:
  raise `min_silence` (default 1000 ms) and `max_silence` (default 3000 ms).
  An elderly or careful audience wants more; a quick back-and-forth wants less.
- **Answering too slowly**: lower them, but expect more interruptions.
- **Talked over on a noisy line**: raise `vad_threshold` (default 0.5) so
  background noise does not count as speech.
- **Lines that must be heard in full**: `uninterruptible_turns` names
  `greeting`, `dtmf_prompt` and `tool_refused_ask`. Caller speech during a
  protected line is discarded, not queued, so protect only what must land: a
  recorded-line notice, a keypad prompt. A reply from your own model cannot be
  protected; put must-say wording in the greeting. This field needs a recent
  SDK; on an older pin it is an unknown argument.
- Set `interrupt_response=False` only for an agent that must never be cut off,
  such as a compliance read-out. Callers find it rude anywhere else.

## Line conditions

- `voice_focus="far-field"` for speakerphones and car calls;
  `"near-field"` (with `voice_focus_threshold`) to ignore a TV or a second
  speaker in the room.

## Other languages

- `language_codes=["es"]` for one language; list several when callers switch.
- Write the system prompt and greeting in that language, and pick a voice that
  speaks it.
- `keyterms` still apply; add local spellings.

## Voices

`voice=` takes a name from the API's list (the SDK reference has it, and an
unknown name is a 422 that lists them all). Pick for the audience and the
brand, then make a test call: a voice that reads well on a laptop can be harsh
over a phone codec.
