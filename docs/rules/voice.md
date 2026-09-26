---
paths:
  - "app/integrations/stt/**"
  - "app/integrations/tts/**"
  - "app/integrations/wakeword/**"
  - "app/modules/voice/**"
  - "app/ws/voice.py"
  - "app/core/audio.py"
  - "desktop/**"
---

# Voice

The reasons and the measurements are `docs/STRUCTURE_DECISION.md` §7. This file is how the code must look.

## The pipeline

`desktop/` captures the microphone as 16 kHz mono int16 and streams it over `WS /ws/voice`. Everything else runs in
the backend: `VoiceSession` cuts the stream into 80 ms chunks (`WAKE_CHUNK_SAMPLES`), feeds the wake word while
`idle`, records until the speaker falls silent, transcribes, asks the brain, synthesizes and sends one WAV back.

| State | Audio is | Leaves on |
|---|---|---|
| `idle` | fed to the wake word and the noise floor | wake word, or `{"type": "listen"}` |
| `listening` | recorded | silence after speech → `thinking`; no speech in `VOICE_START_TIMEOUT_MS` → `idle` |
| `thinking` | ignored | the reply's WAV is sent → `speaking`; an empty transcript or an error → `idle` |
| `speaking` | ignored — the microphone hears the speaker | `{"type": "played"}`, or the WAV's length plus `PLAYBACK_GRACE_S` |

Audio is ignored while thinking and speaking so JARVIS never answers itself.

## Engines

`VoiceEngines` holds three protocols — `Transcriber`, `Speaker`, and a factory for `WakeWordDetector`, one per
session because the detector keeps state. `app/lifespan.py::build_local_voice` builds the local ones; tests pass
fakes from `tests/fakes/voice.py` through `create_app(voice_engines=...)`. A model is loaded once, in a thread, at
startup; inference runs through `anyio.to_thread.run_sync`, never on the event loop.

Heavy libraries are imported inside the engine classes, so importing `app` does not load `torch`.

## Language

- The desktop window sends the owner's choice as `{"type": "language", "language": "uz"|"ru"|"en"|"auto"}` on every
  connect; `VoiceSession.language` holds it and passes it to `Transcriber.transcribe`.
- Uzbek goes to the Uzbek fine-tune (`VOICE_STT_UZ_SOURCE`, converted once to CTranslate2 in `VOICE_STT_UZ_DIR` by
  `ensure_ct2_model` at startup); Russian and English go to `VOICE_STT_MODEL`. On `auto` the general model detects
  among `VOICE_LANGUAGES` only (`pick_language`) — its own guess for Uzbek is Persian or Pashto — and an Uzbek
  result is re-transcribed by the Uzbek model (`uses_uzbek_model`).
- The reply's voice follows the reply text, not the transcript (`reply_language`): Cyrillic → Russian,
  `looks_uzbek` → Uzbek, else the heard language, and English if that was Uzbek. Claude understands a garbled
  Uzbek transcript and answers in Uzbek, so the transcript's language is the weaker signal.
- Uzbek is spoken by MMS after `to_cyrillic`; its tokenizer knows no digits, so `SPOKEN_REPLY_RULES` asks for numbers
  in words.
- Every Cyrillic or Uzbek-apostrophe literal lives in `app/integrations/tts/uzbek.py`, the one file ruff's `RUF001`
  is waived for, with `desktop/window.py` for its Uzbek labels.

## Desktop

`desktop/` is a client: `.importlinter` forbids it to import `app`. JARVIS listens on `JARVIS_PORT`, default 8765 —
not 8000, which the owner's other backends use (on 2026-09-25 `myhelperbot-backend`'s Django held it and JARVIS
started, failed to bind and left the window at "connecting"). `desktop/backend.py` starts the backend with
`python -m uvicorn` when `/health` does not answer `{"status": "ok"}`, refuses with a message when something else
holds the port, stops retrying and shows the log's last error when the backend exits, writes its output to `data/backend.log`, and stops it on close
with `SIGINT` so the lifespan disconnects Claude. Qt's own audio (`QtMultimedia`) is used, so no PortAudio is needed.
