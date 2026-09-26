import numpy as np

from app.core.audio import SAMPLE_RATE, pcm_from_bytes, rms, to_float, to_pcm, wav_bytes, wav_duration


def test_bytes_become_int16_and_a_trailing_odd_byte_is_dropped() -> None:
    assert pcm_from_bytes(b"\x01\x00\x02\x00\x03").tolist() == [1, 2]


def test_rms_of_silence_and_of_a_constant() -> None:
    assert rms(np.zeros(10, dtype=np.int16)) == 0.0
    assert rms(np.full(10, 100, dtype=np.int16)) == 100.0
    assert rms(np.zeros(0, dtype=np.int16)) == 0.0


def test_float_round_trip_keeps_the_signal() -> None:
    pcm = np.array([0, 16384, -16384], dtype=np.int16)

    assert np.allclose(to_float(pcm), [0.0, 0.5, -0.5])
    assert np.abs(to_pcm(to_float(pcm)).astype(int) - pcm).max() <= 1


def test_to_pcm_clips() -> None:
    assert to_pcm(np.array([2.0, -2.0])).tolist() == [32767, -32767]


def test_wav_duration() -> None:
    assert wav_duration(wav_bytes(np.zeros(SAMPLE_RATE // 2, dtype=np.int16), SAMPLE_RATE)) == 0.5
