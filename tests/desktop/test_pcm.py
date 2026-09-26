import numpy as np

from desktop.pcm import level, parse_wav, to_mono_16k


def test_int16_mono_16k_passes_through() -> None:
    samples = np.array([0, 1000, -1000, 32000], dtype=np.int16)

    result = np.frombuffer(to_mono_16k(samples.tobytes(), 16000, 1, "int16"), dtype=np.int16)

    assert np.abs(result.astype(int) - samples).max() <= 1


def test_stereo_48k_int32_becomes_mono_16k() -> None:
    stereo = np.zeros((4800, 2), dtype=np.int32)
    stereo[:, 0] = 2**30

    result = np.frombuffer(to_mono_16k(stereo.tobytes(), 48000, 2, "int32"), dtype=np.int16)

    assert result.size == 1600
    assert abs(int(result[0]) - 8191) <= 2


def test_float_input_is_converted() -> None:
    samples = np.array([0.5, -0.5], dtype=np.float32)

    result = np.frombuffer(to_mono_16k(samples.tobytes(), 16000, 1, "float"), dtype=np.int16)

    assert result.tolist() == [16383, -16383]


def test_wav_is_parsed() -> None:
    import io
    import wave

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(22050)
        wav.writeframes(bytes(100))

    audio = parse_wav(buffer.getvalue())

    assert (audio.sample_rate, audio.channels, audio.sample_width, len(audio.frames)) == (22050, 1, 2, 100)


def test_level_is_between_zero_and_one() -> None:
    assert level(bytes(100)) == 0.0
    assert level(np.full(100, 32000, dtype=np.int16).tobytes()) == 1.0
    assert level(b"") == 0.0
