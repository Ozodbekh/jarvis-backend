from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.core.exceptions import ERROR_MESSAGES
from app.core.logging import get_logger
from app.modules.voice.service import Failed, Heard, Replied, Spoken, StateChanged, VoiceOutput
from app.ws.deps import Voice
from app.ws.schemas import Error, VoiceControl, VoiceHeard, VoiceReply, VoiceStateMessage

logger = get_logger("app.ws.voice")

router = APIRouter()


def _error(code: str) -> Error:
    return Error(code=code, message=ERROR_MESSAGES.get(code, ERROR_MESSAGES["HTTP_ERROR"]))


@router.websocket("/ws/voice")
async def voice_conversation(websocket: WebSocket, voice: Voice) -> None:
    await websocket.accept()

    async def send(output: VoiceOutput) -> None:
        match output:
            case Spoken():
                await websocket.send_bytes(output.wav)
            case StateChanged():
                await websocket.send_text(VoiceStateMessage(state=output.state).model_dump_json())
            case Heard():
                await websocket.send_text(VoiceHeard(text=output.text, language=output.language).model_dump_json())
            case Replied():
                await websocket.send_text(VoiceReply(text=output.text).model_dump_json())
            case Failed():
                await websocket.send_text(_error(output.code).model_dump_json())

    session = voice.open_session(send)
    logger.info("voice_connected")
    try:
        await send(StateChanged(session.state))
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
            if data := message.get("bytes"):
                await session.feed(data)
            elif text := message.get("text"):
                try:
                    control = VoiceControl.model_validate_json(text)
                except ValidationError:
                    await websocket.send_text(_error("VALIDATION_ERROR").model_dump_json())
                    continue
                match control.type:
                    case "listen":
                        await session.listen()
                    case "played":
                        await session.played()
                    case "language":
                        session.set_language(None if control.language in (None, "auto") else control.language)
    except WebSocketDisconnect:
        pass
    finally:
        await session.close()
        logger.info("voice_disconnected")
