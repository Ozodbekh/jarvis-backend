import asyncio
import contextlib

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.core.exceptions import ERROR_MESSAGES, AppError
from app.core.logging import get_logger
from app.integrations.claude.events import BrainEvent, Result, TextDelta, ToolUse
from app.modules.brain.service import BrainService
from app.ws.deps import Brain
from app.ws.schemas import ClientCommand, Delta, Done, Error, ServerMessage, Started, Tool

logger = get_logger("app.ws")

router = APIRouter()


def _to_message(event: BrainEvent) -> ServerMessage:
    match event:
        case TextDelta():
            return Delta(text=event.text)
        case ToolUse():
            return Tool(name=event.name)
        case Result():
            return Done(
                text=event.text, session_id=event.session_id, cost_usd=event.cost_usd, duration_ms=event.duration_ms
            )


def _error(code: str) -> Error:
    return Error(code=code, message=ERROR_MESSAGES.get(code, ERROR_MESSAGES["HTTP_ERROR"]))


class _Conversation:
    def __init__(self, websocket: WebSocket, brain: BrainService) -> None:
        self._websocket = websocket
        self._brain = brain
        self._send_lock = asyncio.Lock()
        self._tasks: set[asyncio.Task[None]] = set()

    async def send(self, message: ServerMessage) -> None:
        async with self._send_lock:
            await self._websocket.send_text(message.model_dump_json())

    def start_command(self, text: str) -> None:
        task = asyncio.create_task(self._run(text))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def cancel_all(self) -> None:
        for task in list(self._tasks):
            task.cancel()
        for task in list(self._tasks):
            with contextlib.suppress(asyncio.CancelledError):
                await task

    async def _run(self, text: str) -> None:
        try:
            events = self._brain.run(text)
            first = True
            async for event in events:
                if first:
                    await self.send(Started())
                    first = False
                await self.send(_to_message(event))
        except AppError as error:
            await self._send_quietly(_error(error.code))
        except WebSocketDisconnect, RuntimeError:
            logger.info("ws_send_failed")
        except Exception:
            logger.exception("ws_command_failed")
            await self._send_quietly(_error("INTERNAL_ERROR"))

    async def _send_quietly(self, message: ServerMessage) -> None:
        with contextlib.suppress(WebSocketDisconnect, RuntimeError):
            await self.send(message)


@router.websocket("/ws")
async def conversation(websocket: WebSocket, brain: Brain) -> None:
    await websocket.accept()
    session = _Conversation(websocket, brain)
    logger.info("ws_connected")
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                command = ClientCommand.model_validate_json(raw)
            except ValidationError:
                await session.send(_error("VALIDATION_ERROR"))
                continue
            session.start_command(command.text)
    except WebSocketDisconnect:
        logger.info("ws_disconnected")
    finally:
        await session.cancel_all()
