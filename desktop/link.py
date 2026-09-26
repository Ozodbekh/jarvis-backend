import json

from PySide6.QtCore import QByteArray, QObject, QTimer, QUrl, Signal
from PySide6.QtWebSockets import QWebSocket

RECONNECT_MS = 2000


class VoiceLink(QObject):
    connected = Signal(bool)
    state = Signal(str)
    heard = Signal(str, str)
    reply = Signal(str)
    error = Signal(str, str)
    speech = Signal(bytes)

    def __init__(self, url: str) -> None:
        super().__init__()
        self._url = QUrl(url)
        self._socket = QWebSocket()
        self._socket.connected.connect(lambda: self.connected.emit(True))
        self._socket.disconnected.connect(self._on_disconnected)
        self._socket.textMessageReceived.connect(self._on_text)
        self._socket.binaryMessageReceived.connect(self._on_binary)
        self._socket.errorOccurred.connect(self._on_error)
        self._retry = QTimer(self)
        self._retry.setSingleShot(True)
        self._retry.timeout.connect(self.open)
        self._closing = False

    @property
    def is_open(self) -> bool:
        return self._socket.isValid()

    def open(self) -> None:
        self._socket.open(self._url)

    def close(self) -> None:
        self._closing = True
        self._retry.stop()
        self._socket.close()

    def send_audio(self, pcm: bytes) -> None:
        if self.is_open:
            self._socket.sendBinaryMessage(QByteArray(pcm))

    def listen(self) -> None:
        self._send_control("listen")

    def played(self) -> None:
        self._send_control("played")

    def set_language(self, language: str) -> None:
        if self.is_open:
            self._socket.sendTextMessage(json.dumps({"type": "language", "language": language}))

    def _send_control(self, kind: str) -> None:
        if self.is_open:
            self._socket.sendTextMessage(json.dumps({"type": kind}))

    def _on_disconnected(self) -> None:
        self.connected.emit(False)
        if not self._closing:
            self._retry.start(RECONNECT_MS)

    def _on_error(self, _error: object) -> None:
        if not self._closing and not self.is_open:
            self._retry.start(RECONNECT_MS)

    def _on_text(self, text: str) -> None:
        message = json.loads(text)
        match message.get("type"):
            case "state":
                self.state.emit(message["state"])
            case "heard":
                self.heard.emit(message["text"], message["language"])
            case "reply":
                self.reply.emit(message["text"])
            case "error":
                self.error.emit(message["code"], message["message"])

    def _on_binary(self, data: QByteArray) -> None:
        self.speech.emit(data.data())
