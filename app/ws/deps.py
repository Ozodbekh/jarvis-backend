from typing import Annotated

from fastapi import Depends
from starlette.requests import HTTPConnection

from app.modules.brain.exceptions import BrainUnavailableError
from app.modules.brain.service import BrainService
from app.modules.voice.exceptions import VoiceUnavailableError
from app.modules.voice.service import VoiceService


def get_brain(connection: HTTPConnection) -> BrainService:
    brain = getattr(connection.app.state, "brain", None)
    if not isinstance(brain, BrainService):
        raise BrainUnavailableError("BRAIN_UNAVAILABLE")
    return brain


Brain = Annotated[BrainService, Depends(get_brain)]


def get_voice(connection: HTTPConnection) -> VoiceService:
    voice = getattr(connection.app.state, "voice", None)
    if not isinstance(voice, VoiceService):
        raise VoiceUnavailableError("VOICE_UNAVAILABLE")
    return voice


Voice = Annotated[VoiceService, Depends(get_voice)]
