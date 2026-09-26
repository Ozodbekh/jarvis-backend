from pathlib import Path

from app.integrations.stt.whisper import pick_language


def test_language_is_picked_among_the_allowed_ones_only() -> None:
    probabilities = [("fa", 0.6), ("uz", 0.01), ("ru", 0.003), ("en", 0.002)]

    assert pick_language(probabilities, ["uz", "ru", "en"]) == "uz"


def test_missing_languages_count_as_zero() -> None:
    assert pick_language([("ru", 0.9)], ["uz", "ru", "en"]) == "ru"


def test_uzbek_goes_to_the_uzbek_model_only_when_it_is_loaded() -> None:
    from app.integrations.stt.whisper import uses_uzbek_model

    assert uses_uzbek_model("uz", has_uzbek_model=True)
    assert not uses_uzbek_model("uz", has_uzbek_model=False)
    assert not uses_uzbek_model("ru", has_uzbek_model=True)


def test_converted_model_is_not_converted_again(tmp_path: Path) -> None:
    from app.integrations.stt.whisper import ensure_ct2_model

    (tmp_path / "model.bin").write_bytes(b"x")

    assert ensure_ct2_model("no/such-model", tmp_path) == tmp_path
