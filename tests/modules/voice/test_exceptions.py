from app.core.exceptions import ERROR_MESSAGES
from app.modules.voice.exceptions import VoiceUnavailableError


def test_voice_unavailable_is_503_with_a_message() -> None:
    error = VoiceUnavailableError("VOICE_UNAVAILABLE")

    assert error.status_code == 503
    assert error.message == ERROR_MESSAGES["VOICE_UNAVAILABLE"]
