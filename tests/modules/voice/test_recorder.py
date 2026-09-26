import numpy as np

from app.modules.voice.recorder import Endpointing, NoiseFloor, RecorderStatus, UtteranceRecorder

ENDPOINTING = Endpointing(min_speech_rms=400, silence_ms=800, start_timeout_ms=2000, max_utterance_s=3)
CHUNK = 1280


def frame(amplitude: int) -> np.ndarray:
    return np.full(CHUNK, amplitude, dtype=np.int16)


def test_speech_then_silence_finishes_the_utterance() -> None:
    recorder = UtteranceRecorder(ENDPOINTING, threshold=400)
    statuses = [recorder.feed(frame(2000)) for _ in range(5)]
    statuses += [recorder.feed(frame(0)) for _ in range(10)]

    assert statuses[-1] is RecorderStatus.DONE
    assert RecorderStatus.DONE not in statuses[:-1]
    assert recorder.audio().size == 15 * CHUNK


def test_nothing_said_before_the_start_timeout() -> None:
    recorder = UtteranceRecorder(ENDPOINTING, threshold=400)
    statuses = [recorder.feed(frame(10)) for _ in range(25)]

    assert statuses[-1] is RecorderStatus.NOTHING_SAID


def test_endless_speech_stops_at_the_maximum() -> None:
    recorder = UtteranceRecorder(ENDPOINTING, threshold=400)
    statuses = [recorder.feed(frame(2000)) for _ in range(38)]

    assert statuses[-1] is RecorderStatus.DONE


def test_noise_floor_ignores_speech() -> None:
    noise = NoiseFloor()
    noise.observe(frame(100), minimum=400)
    noise.observe(frame(5000), minimum=400)

    assert noise.level == 100.0
    assert noise.speech_threshold(400) == 400.0


def test_loud_room_raises_the_threshold() -> None:
    noise = NoiseFloor()
    for _ in range(50):
        noise.observe(frame(300), minimum=400)

    assert noise.speech_threshold(400) == 900.0


def test_empty_recorder_has_no_audio() -> None:
    assert UtteranceRecorder(ENDPOINTING, threshold=400).audio().size == 0
