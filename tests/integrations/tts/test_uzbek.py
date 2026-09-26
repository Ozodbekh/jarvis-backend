import pytest

from app.integrations.tts.uzbek import has_cyrillic, looks_uzbek, to_cyrillic


@pytest.mark.parametrize(
    ("latin", "cyrillic"),
    [
        ("Salom", "салом"),
        ("Oʻzbekiston", "ўзбекистон"),
        ("o'zbek g'alaba", "ўзбек ғалаба"),
        ("choy shahar", "чой шаҳар"),
        ("yoshlar yulduz yaxshi", "ёшлар юлдуз яхши"),
        ("ertaga", "эртага"),
        ("maʼlumot", "маълумот"),
        ("soat 15", "соат 15"),
    ],
)
def test_latin_uzbek_becomes_cyrillic(latin: str, cyrillic: str) -> None:
    assert to_cyrillic(latin) == cyrillic


def test_cyrillic_is_detected() -> None:
    assert has_cyrillic("Привет")
    assert not has_cyrillic("Salom")


@pytest.mark.parametrize(
    "text",
    ["Bugun soat uchda uchrashuv bor.", "Siz bilan gaplashaman.", "Oʻzbekiston"],
)
def test_uzbek_replies_are_recognized(text: str) -> None:
    assert looks_uzbek(text)


@pytest.mark.parametrize("text", ["You have a meeting with Anvar today.", "Hello there"])
def test_english_replies_are_not_uzbek(text: str) -> None:
    assert not looks_uzbek(text)
