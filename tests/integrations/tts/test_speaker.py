import numpy as np

from app.core.audio import Pcm, wav_duration
from app.integrations.tts.speaker import LocalSpeaker, clean_for_speech


class RecordingVoice:
    def __init__(self) -> None:
        self.texts: list[str] = []
        self.loaded = False

    def load(self) -> None:
        self.loaded = True

    def synthesize(self, text: str) -> tuple[Pcm, int]:
        self.texts.append(text)
        return np.zeros(8000, dtype=np.int16), 16000


def test_markdown_is_removed_before_speaking() -> None:
    assert clean_for_speech("**Salom**  #bugun\n`reja`") == "Salom bugun reja"


def test_speaker_picks_the_voice_for_the_language_and_returns_wav() -> None:
    uz, en = RecordingVoice(), RecordingVoice()
    speaker = LocalSpeaker({"uz": uz, "en": en})
    speaker.load()

    speech = speaker.speak("*Salom*", "uz")

    assert uz.loaded and en.loaded
    assert uz.texts == ["Salom"]
    assert speech.language == "uz"
    assert wav_duration(speech.wav) == 0.5


def test_unknown_language_falls_back_to_english() -> None:
    en = RecordingVoice()

    assert LocalSpeaker({"en": en}).speak("Bonjour", "fr").language == "en"
    assert en.texts == ["Bonjour"]
