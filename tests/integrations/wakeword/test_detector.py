from app.integrations.wakeword.detector import WAKE_CHUNK_SAMPLES, WAKE_WORD_MODEL


def test_detector_works_on_openwakeword_chunks_of_80_ms() -> None:
    assert WAKE_CHUNK_SAMPLES == 1280
    assert WAKE_WORD_MODEL == "hey_jarvis"
