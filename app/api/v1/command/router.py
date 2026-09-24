from fastapi import APIRouter

from app.api.deps import Brain
from app.api.v1.command.schemas import CommandRequest, CommandResponse

router = APIRouter(prefix="/command", tags=["command"])


@router.post("")
async def run_command(body: CommandRequest, brain: Brain) -> CommandResponse:
    result = await brain.run_to_end(body.text)
    return CommandResponse.model_validate(result)
