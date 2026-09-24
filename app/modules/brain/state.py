import os
from pathlib import Path

from pydantic import BaseModel, ValidationError

from app.core.logging import get_logger

logger = get_logger("app.brain")


class BrainState(BaseModel):
    session_id: str | None = None
    turns: int = 0


class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> BrainState:
        if not self.path.is_file():
            return BrainState()
        try:
            return BrainState.model_validate_json(self.path.read_bytes())
        except ValidationError:
            logger.warning("state_unreadable", path=str(self.path))
            return BrainState()

    def save(self, state: BrainState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        draft = self.path.with_suffix(".tmp")
        draft.write_text(state.model_dump_json())
        os.replace(draft, self.path)
