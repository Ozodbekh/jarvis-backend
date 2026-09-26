from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QObject, Signal
from PySide6.QtMultimedia import QAudio, QAudioFormat, QAudioSink, QAudioSource, QMediaDevices

from desktop.pcm import TARGET_RATE, level, parse_wav, to_mono_16k

SAMPLE_FORMATS = {
    QAudioFormat.SampleFormat.Int16: "int16",
    QAudioFormat.SampleFormat.Int32: "int32",
    QAudioFormat.SampleFormat.Float: "float",
}


def _wanted_format() -> QAudioFormat:
    audio_format = QAudioFormat()
    audio_format.setSampleRate(TARGET_RATE)
    audio_format.setChannelCount(1)
    audio_format.setSampleFormat(QAudioFormat.SampleFormat.Int16)
    return audio_format


class Microphone(QObject):
    chunk = Signal(bytes)
    level = Signal(float)

    def __init__(self) -> None:
        super().__init__()
        device = QMediaDevices.defaultAudioInput()
        wanted = _wanted_format()
        self._format = wanted if device.isFormatSupported(wanted) else device.preferredFormat()
        self._source = QAudioSource(device, self._format)
        self._device: QIODevice | None = None
        self.muted = False

    @property
    def name(self) -> str:
        return QMediaDevices.defaultAudioInput().description()

    def start(self) -> None:
        self._device = self._source.start()
        self._device.readyRead.connect(self._read)

    def stop(self) -> None:
        self._source.stop()

    def _read(self) -> None:
        if self._device is None:
            return
        raw = bytes(self._device.readAll().data())
        if not raw:
            return
        sample_format = SAMPLE_FORMATS.get(self._format.sampleFormat(), "int16")
        pcm = to_mono_16k(raw, self._format.sampleRate(), self._format.channelCount(), sample_format)
        self.level.emit(0.0 if self.muted else level(pcm))
        if not self.muted:
            self.chunk.emit(pcm)


class Speaker(QObject):
    finished = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._sink: QAudioSink | None = None
        self._buffer: QBuffer | None = None

    def play(self, wav: bytes) -> None:
        self.stop()
        audio = parse_wav(wav)
        audio_format = QAudioFormat()
        audio_format.setSampleRate(audio.sample_rate)
        audio_format.setChannelCount(audio.channels)
        audio_format.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        self._buffer = QBuffer()
        self._buffer.setData(QByteArray(audio.frames))
        self._buffer.open(QIODevice.OpenModeFlag.ReadOnly)
        self._sink = QAudioSink(QMediaDevices.defaultAudioOutput(), audio_format)
        self._sink.stateChanged.connect(self._state_changed)
        self._sink.start(self._buffer)

    def stop(self) -> None:
        if self._sink is not None:
            self._sink.stateChanged.disconnect(self._state_changed)
            self._sink.stop()
        self._sink = None
        self._buffer = None

    def _state_changed(self, state: QAudio.State) -> None:
        if state == QAudio.State.IdleState:
            self.stop()
            self.finished.emit()
