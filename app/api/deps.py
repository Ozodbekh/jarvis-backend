from typing import Annotated

from fastapi import Depends
from starlette.requests import HTTPConnection

from app.modules.brain.exceptions import BrainUnavailableError
from app.modules.brain.service import BrainService


def get_brain(connection: HTTPConnection) -> BrainService:
    brain = getattr(connection.app.state, "brain", None)
    if not isinstance(brain, BrainService):
        raise BrainUnavailableError("BRAIN_UNAVAILABLE")
    return brain


Brain = Annotated[BrainService, Depends(get_brain)]
