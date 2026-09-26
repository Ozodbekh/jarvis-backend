import html

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from desktop.audio import Microphone, Speaker
from desktop.backend import PORT, Backend, StartResult, last_error_line
from desktop.link import VoiceLink

BACKEND_WATCH_MS = 1000
DEFAULT_LANGUAGE = "uz"
LANGUAGES = (("uz", "Oʻzbek"), ("ru", "Русский"), ("en", "English"), ("auto", "Avto (uz / ru / en)"))

STATES = {
    "connecting": ("#5b6475", "Ulanmoqda… birinchi ishga tushishda modellar 1–2 daqiqa yuklanadi"),
    "idle": ("#2f7bff", "Kutyapman — «Hey Jarvis» deng"),
    "listening": ("#35d0ff", "Tinglayapman…"),
    "thinking": ("#ffb020", "O‘ylayapman…"),
    "speaking": ("#27d17f", "Gapiryapman…"),
    "stopped": ("#ff4d5e", "Backend to‘xtadi — data/backend.log ga qarang"),
    "port_taken": ("#ff4d5e", f"{PORT}-port boshqa dastur tomonidan band — JARVIS_PORT bilan boshqa port bering"),
}

STYLE = """
QWidget { background: #05070d; color: #cfe3ff; font-family: 'JetBrains Mono', 'DejaVu Sans Mono', monospace; }
QLabel#title { color: #6fa8ff; font-size: 22px; letter-spacing: 6px; }
QLabel#status { color: #9fb8d9; font-size: 14px; }
QTextBrowser { background: #0a0f1a; border: 1px solid #1b2a44; border-radius: 10px; padding: 10px; font-size: 14px; }
QPushButton { background: #0f1b30; border: 1px solid #2f7bff; border-radius: 8px; padding: 10px 18px; font-size: 14px; }
QPushButton:hover { background: #16294a; }
QPushButton:checked { border-color: #ff4d5e; color: #ff8a95; }
QProgressBar { background: #0a0f1a; border: 1px solid #1b2a44; border-radius: 4px; height: 8px; }
QComboBox { background: #0f1b30; border: 1px solid #2f7bff; border-radius: 8px; padding: 8px 12px; font-size: 14px; }
QComboBox QAbstractItemView { background: #0f1b30; selection-background-color: #16294a; }
QProgressBar::chunk { background: #2f7bff; border-radius: 4px; }
"""


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("JARVIS")
        self.resize(560, 720)
        self.setStyleSheet(STYLE)

        self._backend = Backend()
        self._link = VoiceLink(f"ws://127.0.0.1:{PORT}/ws/voice")
        self._microphone = Microphone()
        self._speaker = Speaker()

        self._orb = QLabel()
        self._orb.setFixedSize(150, 150)
        self._status = QLabel()
        self._status.setObjectName("status")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setWordWrap(True)
        self._level = QProgressBar()
        self._level.setRange(0, 100)
        self._level.setTextVisible(False)
        self._log = QTextBrowser()
        self._talk = QPushButton("Gapirish")
        self._mute = QPushButton("Mikrofonni o‘chirish")
        self._mute.setCheckable(True)
        self._settings = QSettings("jarvis", "desktop")
        self._language = QComboBox()
        for code, label in LANGUAGES:
            self._language.addItem(label, code)
        saved = self._settings.value("language", DEFAULT_LANGUAGE)
        self._language.setCurrentIndex(max(0, self._language.findData(saved)))

        self._build_layout()
        self._connect_signals()
        self._set_state("connecting")

        self._stopped = False
        self._watch = QTimer(self)
        self._watch.timeout.connect(self._watch_backend)
        self._watch.start(BACKEND_WATCH_MS)

    def start(self) -> None:
        self._note(f"Mikrofon: {html.escape(self._microphone.name)}")
        if self._backend.ensure_started() is StartResult.PORT_TAKEN:
            self._stop_trying("port_taken")
            return
        self._microphone.start()
        self._link.open()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        self._watch.stop()
        self._microphone.stop()
        self._speaker.stop()
        self._link.close()
        self._backend.stop()
        event.accept()

    def _build_layout(self) -> None:
        title = QLabel("J.A.R.V.I.S.")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        orb_row = QHBoxLayout()
        orb_row.addStretch()
        orb_row.addWidget(self._orb)
        orb_row.addStretch()

        buttons = QHBoxLayout()
        buttons.addWidget(self._language)
        buttons.addWidget(self._talk)
        buttons.addWidget(self._mute)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        layout.addWidget(title)
        layout.addLayout(orb_row)
        layout.addWidget(self._status)
        layout.addWidget(self._level)
        layout.addWidget(self._log, stretch=1)
        layout.addLayout(buttons)

        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

    def _connect_signals(self) -> None:
        self._microphone.chunk.connect(self._link.send_audio)
        self._microphone.level.connect(lambda value: self._level.setValue(int(value * 100)))
        self._link.connected.connect(self._on_connected)
        self._link.state.connect(self._set_state)
        self._link.heard.connect(lambda text, language: self._say("Siz", text, "#8fd3ff", language))
        self._link.reply.connect(lambda text: self._say("JARVIS", text, "#7dffb3"))
        self._link.error.connect(self._on_error)
        self._link.speech.connect(self._speaker.play)
        self._speaker.finished.connect(self._link.played)
        self._talk.clicked.connect(self._link.listen)
        self._mute.toggled.connect(self._on_mute)
        self._language.currentIndexChanged.connect(self._on_language)

    def _set_state(self, state: str) -> None:
        color, text = STATES.get(state, STATES["idle"])
        red, green, blue = (int(color[index : index + 2], 16) for index in (1, 3, 5))
        self._orb.setStyleSheet(
            f"background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,"
            f" stop:0 {color}, stop:0.55 rgba({red}, {green}, {blue}, 70), stop:1 #05070d);"
            f" border: 2px solid {color}; border-radius: 75px;"
        )
        self._status.setText(text)
        self._talk.setEnabled(state == "idle")

    def _selected_language(self) -> str:
        return str(self._language.currentData())

    def _on_language(self, _index: int) -> None:
        code = self._selected_language()
        self._settings.setValue("language", code)
        self._link.set_language(code)
        self._note(f"Til: {html.escape(self._language.currentText())}")

    def _on_connected(self, connected: bool) -> None:
        if connected:
            self._link.set_language(self._selected_language())
            self._note(f"Backend'ga ulandi. Til: {html.escape(self._language.currentText())}")
        elif not self._stopped:
            self._set_state("connecting")

    def _on_error(self, code: str, message: str) -> None:
        self._note(f"<span style='color:#ff8a95'>{html.escape(code)}: {html.escape(message)}</span>")

    def _on_mute(self, muted: bool) -> None:
        self._microphone.muted = muted
        self._mute.setText("Mikrofonni yoqish" if muted else "Mikrofonni o‘chirish")

    def _watch_backend(self) -> None:
        if self._backend.exited():
            self._stop_trying("stopped")
            if error := last_error_line():
                self._note(f"<span style='color:#ff8a95'>{html.escape(error)}</span>")

    def _stop_trying(self, state: str) -> None:
        self._stopped = True
        self._watch.stop()
        self._link.close()
        self._set_state(state)

    def _say(self, who: str, text: str, color: str, language: str = "") -> None:
        tag = f" <span style='color:#5b6475'>[{html.escape(language)}]</span>" if language else ""
        self._log.append(f"<p><b style='color:{color}'>{who}</b>{tag}: {html.escape(text)}</p>")

    def _note(self, text: str) -> None:
        self._log.append(f"<p style='color:#5b6475'>{text}</p>")
