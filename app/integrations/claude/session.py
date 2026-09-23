import asyncio
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from typing import Protocol

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, ClaudeSDKError, Message

from app.core.config import Settings
from app.core.logging import get_logger
from app.integrations.claude.events import BrainEvent, from_sdk_message
from app.integrations.claude.options import build_options

logger = get_logger("app.claude")


class ClaudeUnavailableError(Exception):
    pass


class ClaudeSession(Protocol):
    @property
    def is_running(self) -> bool: ...

    async def start(self, session_id: str | None) -> None: ...

    def ask(self, prompt: str) -> AsyncIterator[BrainEvent]: ...

    async def interrupt(self) -> None: ...

    async def stop(self) -> None: ...


class SdkClient(Protocol):
    async def connect(self) -> None: ...

    async def query(self, prompt: str) -> None: ...

    def receive_response(self) -> AsyncIterator[Message]: ...

    async def interrupt(self) -> None: ...

    async def disconnect(self) -> None: ...


type ClientFactory = Callable[[ClaudeAgentOptions], SdkClient]


@dataclass(frozen=True, slots=True)
class _End:
    pass


@dataclass(frozen=True, slots=True)
class _Failure:
    error: Exception


type _Outcome = BrainEvent | _End | _Failure


@dataclass(slots=True)
class _Request:
    prompt: str
    outcomes: asyncio.Queue[_Outcome] = field(default_factory=asyncio.Queue)


class SdkClaudeSession:
    def __init__(self, settings: Settings, client_factory: ClientFactory = ClaudeSDKClient) -> None:
        self._settings = settings
        self._client_factory = client_factory
        self._client: SdkClient | None = None
        self._requests: asyncio.Queue[_Request | None] = asyncio.Queue()
        self._owner: asyncio.Task[None] | None = None

    @property
    def is_running(self) -> bool:
        return self._owner is not None and not self._owner.done()

    async def start(self, session_id: str | None) -> None:
        await self.stop()
        connected: asyncio.Future[None] = asyncio.get_running_loop().create_future()
        self._requests = asyncio.Queue()
        self._owner = asyncio.create_task(self._own(build_options(self._settings, session_id), connected))
        try:
            await connected
        except Exception as error:
            self._owner = None
            raise ClaudeUnavailableError(str(error)) from error

    async def stop(self) -> None:
        if not self.is_running:
            self._owner = None
            return
        assert self._owner is not None
        await self.interrupt()
        await self._requests.put(None)
        await self._owner
        self._owner = None

    async def interrupt(self) -> None:
        if self._client is None:
            return
        try:
            await self._client.interrupt()
        except ClaudeSDKError:
            logger.warning("interrupt_failed", exc_info=True)

    async def ask(self, prompt: str) -> AsyncIterator[BrainEvent]:
        if not self.is_running:
            raise ClaudeUnavailableError("session is not running")
        request = _Request(prompt)
        await self._requests.put(request)
        while True:
            outcome = await request.outcomes.get()
            match outcome:
                case _End():
                    return
                case _Failure(error=error):
                    raise ClaudeUnavailableError(str(error)) from error
                case _:
                    yield outcome

    async def _own(self, options: ClaudeAgentOptions, connected: asyncio.Future[None]) -> None:
        client = self._client_factory(options)
        try:
            await client.connect()
        except Exception as error:
            connected.set_exception(error)
            return
        self._client = client
        connected.set_result(None)
        logger.info("claude_connected", resumed=options.resume is not None)
        try:
            while (request := await self._requests.get()) is not None:
                await self._serve(client, request)
        finally:
            self._client = None
            await client.disconnect()
            logger.info("claude_disconnected")

    async def _serve(self, client: SdkClient, request: _Request) -> None:
        try:
            await client.query(request.prompt)
            async for message in client.receive_response():
                for event in from_sdk_message(message):
                    request.outcomes.put_nowait(event)
        except Exception as error:
            logger.warning("claude_request_failed", error_type=type(error).__name__)
            request.outcomes.put_nowait(_Failure(error))
        finally:
            request.outcomes.put_nowait(_End())
