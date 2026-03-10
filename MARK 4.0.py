import os
import json
import ast
import threading
import time
import math
from dataclasses import dataclass, field
from typing import Any, List, Optional

import pandas as pd
import pyautogui
from PyQt5.QtCore import QPoint, Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon, QColor, QPainter, QPen, QLinearGradient, QPixmap
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from pynput.keyboard import Key, Listener as KeyboardListener
from pynput.mouse import Listener as MouseListener


translations = {
    "en": {
        "View": "View",
        "Light Mode": "Light Mode",
        "Dark Mode": "Dark Mode",
        "Record": "Record",
        "Stop": "Stop",
        "Clear": "Clear",
        "Replay Actions": "Replay Actions",
        "Preview Nodes": "Pause/Resume Replay",
        "Import CSV": "Import CSV",
        "Export Actions": "Export Actions",
        "Generate Node Code": "Generate Node Code",
        "Edit CSV": "Edit CSV",
        "Repetition Count": "Repetition Count",
        "Time Sleep Value:": "Time Sleep Value:",
        "Enable CSV Field Selection": "Enable CSV Field Selection",
        "Recording... Press \"Stop\" to finish.": "Recording... Press \"Stop\" to finish.",
        "CSV file imported successfully.": "CSV file imported successfully.",
        "Error importing CSV:": "Error importing CSV:",
        "No actions recorded to export.": "No actions recorded to export.",
        "No CSV file imported.": "No CSV file imported.",
        "CSV file opened for editing.": "CSV file opened for editing.",
        "Pause/Resume": "Pause/Resume",
        "click": "click",
        "press": "press",
        "hotkey": "hotkey",
        "scroll": "scroll",
    },
    "pt": {
        "View": "Visualizar",
        "Light Mode": "Modo Claro",
        "Dark Mode": "Modo Escuro",
        "Record": "Gravar",
        "Stop": "Parar",
        "Clear": "Limpar",
        "Replay Actions": "Reproduzir Acoes",
        "Preview Nodes": "Pausar/Continuar Reproducao",
        "Import CSV": "Importar CSV",
        "Export Actions": "Exportar Acoes",
        "Generate Node Code": "Gerar Codigo de No",
        "Edit CSV": "Editar CSV",
        "Repetition Count": "Contagem de Repeticoes",
        "Time Sleep Value:": "Valor de Pausa:",
        "Enable CSV Field Selection": "Habilitar Selecao de Campo CSV",
        "Recording... Press \"Stop\" to finish.": "Gravando... Pressione \"Parar\" para finalizar.",
        "CSV file imported successfully.": "Arquivo CSV importado com sucesso.",
        "Error importing CSV:": "Erro ao importar CSV:",
        "No actions recorded to export.": "Nenhuma acao gravada para exportar.",
        "No CSV file imported.": "Nenhum arquivo CSV importado.",
        "CSV file opened for editing.": "Arquivo CSV aberto para edicao.",
        "Pause/Resume": "Pausar/Continuar",
        "click": "clique",
        "press": "pressionar",
        "hotkey": "atalho",
        "scroll": "scroll",
    },
}


@dataclass
class Action:
    action_type: str
    value: Any


@dataclass
class Node:
    name: str
    actions: List[Action] = field(default_factory=list)


class RecordingOverlay(QWidget):
    start_record_signal = pyqtSignal()
    pause_resume_record_signal = pyqtSignal()
    stop_record_signal = pyqtSignal()
    add_csv_placeholder_signal = pyqtSignal(str)
    move_target_signal = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        # Keep overlay as a top-level tool window so it stays visible even when main window is minimized.
        super().__init__(None)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Recording Overlay")
        self.setGeometry(0, 0, 360, 180)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        layout = QVBoxLayout()
        self.setLayout(layout)
        self.setStyleSheet(
            """
            background: rgba(8, 14, 18, 235);
            color: #f2f6f8;
            font-size: 14px;
            border: 2px solid #8fd3ff;
            border-radius: 12px;
            """
        )

        self.label = QLabel('Recording... Press "Stop" to finish.')
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        self.placeholder_status = QLabel("Tip: click target field, then add placeholder")
        self.placeholder_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.placeholder_status)

        controls = QHBoxLayout()
        layout.addLayout(controls)

        play_button = QPushButton("Play")
        play_button.clicked.connect(self.start_record_signal.emit)
        controls.addWidget(play_button)

        pause_button = QPushButton("Pause")
        pause_button.clicked.connect(self.pause_resume_record_signal.emit)
        controls.addWidget(pause_button)

        stop_button = QPushButton("Stop")
        stop_button.clicked.connect(self.stop_record_signal.emit)
        controls.addWidget(stop_button)

        csv_controls = QHBoxLayout()
        layout.addLayout(csv_controls)

        self.csv_placeholder_combo = QComboBox()
        self.csv_placeholder_combo.setPlaceholderText("CSV Column")
        csv_controls.addWidget(self.csv_placeholder_combo)

        self.add_csv_placeholder_button = QPushButton("Add Placeholder")
        self.add_csv_placeholder_button.clicked.connect(self.emit_csv_placeholder)
        csv_controls.addWidget(self.add_csv_placeholder_button)

        target_controls = QHBoxLayout()
        layout.addLayout(target_controls)

        self.move_target_button = QPushButton("Move Target")
        self.move_target_button.clicked.connect(self.move_target_signal.emit)
        target_controls.addWidget(self.move_target_button)

    def set_csv_columns(self, columns: List[str]):
        self.csv_placeholder_combo.clear()
        self.csv_placeholder_combo.addItems(columns)
        self.add_csv_placeholder_button.setEnabled(bool(columns))

    def emit_csv_placeholder(self):
        selected = self.csv_placeholder_combo.currentText().strip()
        if selected:
            self.add_csv_placeholder_signal.emit(selected)

    def set_placeholder_status(self, text: str):
        self.placeholder_status.setText(text)


class MarkIntroDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Mark Intro")
        self.setFixedSize(680, 280)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        container = QFrame()
        container.setObjectName("introCard")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(26, 22, 26, 22)
        layout.setSpacing(10)

        title = QLabel("MARK")
        title.setObjectName("introTitle")
        subtitle = QLabel("Tranquility Operations Console")
        subtitle.setObjectName("introSubtitle")
        quote = QLabel('"Good afternoon, Mark speaking. Please tell me how may I direct your call."')
        quote.setWordWrap(True)
        quote.setObjectName("introQuote")

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(quote)

        outer = QVBoxLayout(self)
        outer.addWidget(container)

        self.setStyleSheet(
            """
            QFrame#introCard {
                background-color: #101512;
                border: 1px solid #8f7a56;
                border-radius: 14px;
            }
            QLabel#introTitle {
                color: #d9c19a;
                font-size: 30px;
                letter-spacing: 3px;
                font-weight: 700;
            }
            QLabel#introSubtitle {
                color: #98b5a7;
                font-size: 13px;
                letter-spacing: 1px;
            }
            QLabel#introQuote {
                color: #e7dfcf;
                font-size: 15px;
                padding-top: 12px;
            }
            """
        )

        QTimer.singleShot(2400, self.accept)


class MarkHoloCubeWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setMinimumSize(140, 140)
        self.angle = 0.0
        self.running = False
        self.paused = False
        self.base_color = QColor("#78c4ad")

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.advance)
        self.timer.start(35)

    def set_state(self, running: bool, paused: bool):
        self.running = running
        self.paused = paused
        if running and not paused:
            self.base_color = QColor("#78c4ad")
        elif running and paused:
            self.base_color = QColor("#d9c19a")
        else:
            self.base_color = QColor("#7f8a83")
        self.update()

    def advance(self):
        if self.running and not self.paused:
            self.angle = (self.angle + 2.2) % 360
            self.update()

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(0, 0, 0, 0))
        gradient.setColorAt(1, QColor(120, 196, 173, 28))
        painter.fillRect(self.rect(), gradient)

        cx = self.width() / 2
        cy = self.height() / 2
        size = min(self.width(), self.height()) * 0.29

        rad = math.radians(self.angle)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)

        def rotate(px, py):
            return (px * cos_a - py * sin_a, px * sin_a + py * cos_a)

        front = [(-size, -size), (size, -size), (size, size), (-size, size)]
        back = []
        offset = size * 0.56
        for px, py in front:
            rx, ry = rotate(px, py)
            back.append((rx + offset, ry - offset))

        pen = QPen(self.base_color, 2)
        painter.setPen(pen)

        for i in range(4):
            x1, y1 = front[i]
            x2, y2 = front[(i + 1) % 4]
            painter.drawLine(int(cx + x1), int(cy + y1), int(cx + x2), int(cy + y2))

            bx1, by1 = back[i]
            bx2, by2 = back[(i + 1) % 4]
            painter.drawLine(int(cx + bx1), int(cy + by1), int(cx + bx2), int(cy + by2))

            painter.drawLine(int(cx + x1), int(cy + y1), int(cx + bx1), int(cy + by1))

        glow_pen = QPen(QColor(self.base_color.red(), self.base_color.green(), self.base_color.blue(), 80), 4)
        painter.setPen(glow_pen)
        painter.drawEllipse(int(cx - size * 1.3), int(cy - size * 1.3), int(size * 2.6), int(size * 2.6))


class PlaceholderPulseOverlay(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(None)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.center = QPoint(0, 0)
        self.radius = 10
        self.max_radius = 54
        self.steps_left = 0
        self.color = QColor("#79f0b2")

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)

    def flash(self, global_x: int, global_y: int, color: QColor):
        screen = QApplication.primaryScreen()
        if screen is None:
            return

        self.setGeometry(screen.geometry())
        self.center = QPoint(global_x - self.geometry().x(), global_y - self.geometry().y())
        self.radius = 10
        self.steps_left = 12
        self.color = color
        self.show()
        self.raise_()
        self.timer.start(30)

    def tick(self):
        self.radius += 4
        self.steps_left -= 1
        if self.steps_left <= 0 or self.radius > self.max_radius:
            self.timer.stop()
            self.hide()
        self.update()

    def paintEvent(self, event):
        del event
        if not self.isVisible():
            return

        alpha = max(0, 230 - self.radius * 3)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        pen = QPen(QColor(self.color.red(), self.color.green(), self.color.blue(), alpha), 3)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(self.center, self.radius, self.radius)

        center_pen = QPen(QColor(self.color.red(), self.color.green(), self.color.blue(), min(255, alpha + 30)), 2)
        painter.setPen(center_pen)
        painter.drawEllipse(self.center, 6, 6)


class TargetMarkerOverlay(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(None)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.center = QPoint(0, 0)
        self.marker_color = QColor("#ff9a6b")

    def show_at(self, global_x: int, global_y: int, color: QColor):
        screen = QApplication.primaryScreen()
        if screen is None:
            return

        if self.geometry() != screen.geometry():
            self.setGeometry(screen.geometry())
        self.center = QPoint(global_x - self.geometry().x(), global_y - self.geometry().y())
        self.marker_color = color
        if not self.isVisible():
            self.show()
            self.raise_()
        self.update()

    def hide_marker(self):
        self.hide()

    def paintEvent(self, event):
        del event
        if not self.isVisible():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        outer_pen = QPen(self.marker_color, 3)
        painter.setPen(outer_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(self.center, 20, 20)

        cross_pen = QPen(QColor(self.marker_color.red(), self.marker_color.green(), self.marker_color.blue(), 220), 2)
        painter.setPen(cross_pen)
        painter.drawLine(self.center.x() - 10, self.center.y(), self.center.x() + 10, self.center.y())
        painter.drawLine(self.center.x(), self.center.y() - 10, self.center.x(), self.center.y() + 10)


class ActionRecorder(QMainWindow):
    update_preview_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mark: Action Recorder")
        self.setGeometry(100, 100, 1080, 620)
        self.language_code = "pt"
        self.dark_mode = False

        self.nodes: List[Node] = []
        self.current_actions: List[Action] = []
        self.undo_stack: List[dict] = []
        self.redo_stack: List[dict] = []
        self.selected_node_index: Optional[int] = None
        self.node_counter = 1
        self.is_updating_preview = False
        self.mark_state = "idle"

        self.recording = False
        self.record_paused = False
        self.replaying = False
        self.replay_paused = False

        self.mouse_listener: Optional[MouseListener] = None
        self.keyboard_listener: Optional[KeyboardListener] = None

        self.replay_thread: Optional[threading.Thread] = None
        self.stop_replay_event = threading.Event()

        self.tabela: Optional[pd.DataFrame] = None
        self.csv_filename: Optional[str] = None
        self.time_sleep_value = 0.25
        self.mark_idle_icon_path = os.path.join(os.path.dirname(__file__), "m_icon.png")
        self.last_record_click_position: Optional[tuple] = None
        self.placeholder_pulse_overlay = PlaceholderPulseOverlay()
        self.target_marker_overlay = TargetMarkerOverlay()
        self.move_target_mode = False
        self.was_paused_before_move = False
        self.last_move_preview_ts = 0.0

        self.init_ui()
        self.update_ui_texts()
        self.change_theme(self.dark_mode)
        self.set_font()

        icon_path = os.path.join(os.path.dirname(__file__), "MARK 4.0.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

    def init_ui(self):
        main_layout = QHBoxLayout()
        left_layout = QVBoxLayout()
        right_layout = QVBoxLayout()
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)
        main_layout.addLayout(left_layout)
        main_layout.addLayout(right_layout)

        self.mark_header = QFrame()
        self.mark_header.setObjectName("markHeader")
        header_layout = QHBoxLayout(self.mark_header)
        header_layout.setContentsMargins(14, 10, 14, 10)

        title_box = QVBoxLayout()
        title_row = QHBoxLayout()
        self.mark_title_icon = QLabel()
        title_icon = QPixmap(self.mark_idle_icon_path)
        if not title_icon.isNull():
            self.mark_title_icon.setPixmap(title_icon.scaled(30, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.mark_title_icon.setFixedSize(34, 34)
        self.mark_title_icon.setAlignment(Qt.AlignCenter)

        self.mark_title = QLabel("MARK")
        self.mark_title.setObjectName("markTitle")
        title_row.addWidget(self.mark_title_icon)
        title_row.addWidget(self.mark_title)
        title_row.addStretch()

        self.mark_subtitle = QLabel("Tranquility Base Operations")
        self.mark_subtitle.setObjectName("markSubtitle")
        title_box.addLayout(title_row)
        title_box.addWidget(self.mark_subtitle)

        self.mark_status_chip = QLabel()
        self.mark_status_chip.setObjectName("markStatusChip")
        self.mark_status_chip.setAlignment(Qt.AlignCenter)
        self.mark_status_chip.setMinimumWidth(140)
        self.mark_status_chip.setMinimumHeight(86)

        header_layout.addLayout(title_box)
        header_layout.addStretch()
        header_layout.addWidget(self.mark_status_chip)

        left_layout.addWidget(self.mark_header)

        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        edit_menu = menubar.addMenu("Edit")
        language_menu = menubar.addMenu("Language")
        view_menu = menubar.addMenu("View")

        record_action = QAction("Record", self)
        record_action.triggered.connect(self.start_record)
        file_menu.addAction(record_action)

        stop_action = QAction("Stop", self)
        stop_action.triggered.connect(self.stop_record)
        file_menu.addAction(stop_action)

        save_project_action = QAction("Save Project", self)
        save_project_action.triggered.connect(self.save_project)
        file_menu.addAction(save_project_action)

        load_project_action = QAction("Load Project", self)
        load_project_action.triggered.connect(self.load_project)
        file_menu.addAction(load_project_action)

        clear_action = QAction("Clear", self)
        clear_action.triggered.connect(self.clear_actions)
        edit_menu.addAction(clear_action)

        undo_action = QAction("Undo", self)
        undo_action.triggered.connect(self.undo_action)
        edit_menu.addAction(undo_action)

        redo_action = QAction("Redo", self)
        redo_action.triggered.connect(self.redo_action)
        edit_menu.addAction(redo_action)

        en_action = QAction("English", self)
        en_action.triggered.connect(lambda: self.load_translation("en"))
        language_menu.addAction(en_action)

        pt_action = QAction("Portuguese", self)
        pt_action.triggered.connect(lambda: self.load_translation("pt"))
        language_menu.addAction(pt_action)

        light_action = QAction("Light Mode", self)
        light_action.triggered.connect(lambda: self.change_theme(False))
        view_menu.addAction(light_action)

        dark_action = QAction("Dark Mode", self)
        dark_action.triggered.connect(lambda: self.change_theme(True))
        view_menu.addAction(dark_action)

        self.replay_button = QPushButton()
        self.pause_button = QPushButton()
        self.import_csv_button = QPushButton()
        self.export_button = QPushButton()
        self.generate_node_code_button = QPushButton()
        self.edit_csv_button = QPushButton()

        self.replay_button.clicked.connect(self.start_replay)
        self.pause_button.clicked.connect(self.pause_resume_replay)
        self.import_csv_button.clicked.connect(self.import_csv)
        self.export_button.clicked.connect(self.export_actions)
        self.generate_node_code_button.clicked.connect(self.generate_node_code)
        self.edit_csv_button.clicked.connect(self.edit_csv)

        self.headers_combobox = QComboBox()
        self.headers_combobox.setPlaceholderText("CSV header")

        self.repetition_lineedit = QLineEdit()

        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)

        self.node_list = QListWidget()
        self.node_list.itemSelectionChanged.connect(self.update_code_preview_from_node)

        left_layout.addWidget(self.replay_button)
        left_layout.addWidget(self.pause_button)
        left_layout.addWidget(self.import_csv_button)
        left_layout.addWidget(self.export_button)
        left_layout.addWidget(QLabel("Header/Column"))
        left_layout.addWidget(self.headers_combobox)
        left_layout.addWidget(self.repetition_lineedit)
        left_layout.addWidget(self.generate_node_code_button)
        left_layout.addWidget(self.edit_csv_button)
        left_layout.addWidget(self.terminal)
        left_layout.addWidget(self.node_list)

        record_controls = QHBoxLayout()
        self.start_record_button = QPushButton()
        self.pause_record_button = QPushButton()
        self.stop_record_button = QPushButton()

        self.start_record_button.clicked.connect(self.start_record)
        self.pause_record_button.clicked.connect(self.pause_resume_record)
        self.stop_record_button.clicked.connect(self.stop_record)

        record_controls.addWidget(self.start_record_button)
        record_controls.addWidget(self.pause_record_button)
        record_controls.addWidget(self.stop_record_button)
        left_layout.addLayout(record_controls)

        self.code_preview = QTextEdit()
        self.code_preview.setReadOnly(False)
        self.code_preview.textChanged.connect(self.update_actions_from_code)
        self.code_preview.setObjectName("markEditor")
        right_layout.addWidget(self.code_preview)

        csv_layout = QVBoxLayout()
        self.csv_field_checkbox = QCheckBox()
        self.csv_field_checkbox.setChecked(False)
        self.csv_field_checkbox.stateChanged.connect(self.enable_csv_field_selection)
        csv_layout.addWidget(self.csv_field_checkbox)

        self.csv_fields_combobox = QComboBox()
        self.csv_fields_combobox.setEnabled(False)
        csv_layout.addWidget(self.csv_fields_combobox)

        time_sleep_layout = QHBoxLayout()
        self.time_sleep_label = QLabel()
        self.time_sleep_selector = QLineEdit()
        self.time_sleep_selector.setText(str(self.time_sleep_value))
        self.time_sleep_selector.textChanged.connect(self.update_time_sleep_value)
        time_sleep_layout.addWidget(self.time_sleep_label)
        time_sleep_layout.addWidget(self.time_sleep_selector)
        csv_layout.addLayout(time_sleep_layout)
        right_layout.addLayout(csv_layout)

        self.mark_panel = QFrame()
        self.mark_panel.setObjectName("markPanel")
        mark_panel_layout = QVBoxLayout(self.mark_panel)
        mark_panel_layout.setContentsMargins(14, 10, 14, 10)

        self.mark_panel_title = QLabel("MARK SIGNAL")
        self.mark_panel_title.setObjectName("markPanelTitle")
        self.mark_holo_cube = MarkHoloCubeWidget()
        self.mark_quote_label = QLabel("Console online. Awaiting direction.")
        self.mark_quote_label.setObjectName("markQuote")
        self.mark_quote_label.setWordWrap(True)

        mark_panel_layout.addWidget(self.mark_panel_title)
        mark_panel_layout.addWidget(self.mark_holo_cube, alignment=Qt.AlignCenter)
        mark_panel_layout.addWidget(self.mark_quote_label)
        right_layout.addWidget(self.mark_panel)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        self.update_preview_signal.connect(self.update_preview_code)

        self.overlay = RecordingOverlay()
        self.overlay.start_record_signal.connect(self.start_record)
        self.overlay.pause_resume_record_signal.connect(self.pause_resume_record)
        self.overlay.stop_record_signal.connect(self.stop_record)
        self.overlay.add_csv_placeholder_signal.connect(self.add_csv_placeholder_action)
        self.overlay.move_target_signal.connect(self.toggle_move_target_mode)
        self.apply_mark_state("idle")

    def load_translation(self, language_code: str):
        self.language_code = language_code if language_code in translations else "en"
        self.update_ui_texts()

    def update_ui_texts(self):
        self.setWindowTitle("Mark: Action Recorder")
        self.replay_button.setText(self.translate("Replay Actions"))
        self.pause_button.setText(self.translate("Preview Nodes"))
        self.import_csv_button.setText(self.translate("Import CSV"))
        self.export_button.setText(self.translate("Export Actions"))
        self.generate_node_code_button.setText(self.translate("Generate Node Code"))
        self.edit_csv_button.setText(self.translate("Edit CSV"))
        self.repetition_lineedit.setPlaceholderText(self.translate("Repetition Count"))
        self.csv_field_checkbox.setText(self.translate("Enable CSV Field Selection"))
        self.code_preview.setPlaceholderText("Preview Code (Editable)")
        self.start_record_button.setText(self.translate("Record"))
        self.pause_record_button.setText(self.translate("Pause/Resume"))
        self.stop_record_button.setText(self.translate("Stop"))
        self.time_sleep_label.setText(self.translate("Time Sleep Value:"))
        self.overlay.label.setText(self.translate('Recording... Press "Stop" to finish.'))
        self.mark_panel_title.setText("MARK SIGNAL")

    def apply_mark_state(self, state: str):
        self.mark_state = state
        if state == "recording":
            self.mark_status_chip.setPixmap(QPixmap())
            self.mark_status_chip.setText("RECORDING")
            self.mark_status_chip.setStyleSheet("background:#7dc8ae; color:#11211b; border-radius:12px; padding:6px 12px; font-weight:700;")
            self.mark_quote_label.setText("Recording in progress. Please hold your position.")
            self.mark_holo_cube.set_state(True, False)
        elif state == "record_paused":
            self.mark_status_chip.setPixmap(QPixmap())
            self.mark_status_chip.setText("REC PAUSED")
            self.mark_status_chip.setStyleSheet("background:#dcc39a; color:#292014; border-radius:12px; padding:6px 12px; font-weight:700;")
            self.mark_quote_label.setText("Recording paused. Mark is standing by.")
            self.mark_holo_cube.set_state(True, True)
        elif state == "replaying":
            self.mark_status_chip.setPixmap(QPixmap())
            self.mark_status_chip.setText("EXECUTING")
            self.mark_status_chip.setStyleSheet("background:#88d0ba; color:#11211b; border-radius:12px; padding:6px 12px; font-weight:700;")
            self.mark_quote_label.setText("Workflow executing. Keep this channel clear.")
            self.mark_holo_cube.set_state(True, False)
        elif state == "replay_paused":
            self.mark_status_chip.setPixmap(QPixmap())
            self.mark_status_chip.setText("EXEC PAUSED")
            self.mark_status_chip.setStyleSheet("background:#d3b686; color:#2a2216; border-radius:12px; padding:6px 12px; font-weight:700;")
            self.mark_quote_label.setText("Execution paused. Awaiting your command.")
            self.mark_holo_cube.set_state(True, True)
        elif state == "editing":
            self.mark_status_chip.setPixmap(QPixmap())
            self.mark_status_chip.setText("EDITING")
            self.mark_status_chip.setStyleSheet("background:#9db0a8; color:#1c2823; border-radius:12px; padding:6px 12px; font-weight:700;")
            self.mark_quote_label.setText("Editing timeline. Confirm each line before dispatch.")
            self.mark_holo_cube.set_state(False, False)
        else:
            self.mark_status_chip.setStyleSheet("background:#8a968f; color:#16211d; border-radius:12px; padding:4px;")
            self.mark_status_chip.setPixmap(QPixmap())
            self.mark_status_chip.setText("IDLE")
            self.mark_quote_label.setText("Good afternoon. Mark speaking. How may I direct your call?")
            self.mark_holo_cube.set_state(False, False)

    def translate(self, text: str) -> str:
        return translations.get(self.language_code, translations["en"]).get(text, text)

    def update_time_sleep_value(self, value: str):
        if not value.strip():
            return
        try:
            parsed = float(value)
            if parsed < 0:
                raise ValueError
            self.time_sleep_value = parsed
        except ValueError:
            self.print_terminal("Valor de pausa invalido. Use numero >= 0.")

    def clone_nodes(self, nodes: List[Node]) -> List[Node]:
        return [Node(node.name, [Action(a.action_type, a.value) for a in node.actions]) for node in nodes]

    def build_snapshot(self) -> dict:
        return {
            "nodes": self.clone_nodes(self.nodes),
            "selected_node_index": self.selected_node_index,
            "node_counter": self.node_counter,
        }

    def restore_snapshot(self, snapshot: dict):
        self.nodes = self.clone_nodes(snapshot.get("nodes", []))
        self.selected_node_index = snapshot.get("selected_node_index")
        self.node_counter = snapshot.get("node_counter", len(self.nodes) + 1)

        if self.selected_node_index is not None and self.selected_node_index >= len(self.nodes):
            self.selected_node_index = len(self.nodes) - 1 if self.nodes else None

    def snapshot_for_undo(self):
        snapshot = self.build_snapshot()
        self.undo_stack.append(snapshot)
        self.redo_stack.clear()

    def nodes_to_dict(self) -> dict:
        return {
            "version": 1,
            "settings": {
                "time_sleep_value": self.time_sleep_value,
                "language_code": self.language_code,
                "dark_mode": self.dark_mode,
                "csv_filename": self.csv_filename,
            },
            "nodes": [
                {
                    "name": node.name,
                    "actions": [
                        {"type": action.action_type, "value": action.value} for action in node.actions
                    ],
                }
                for node in self.nodes
            ],
        }

    def load_project_from_dict(self, data: dict):
        settings = data.get("settings", {})
        loaded_nodes = []
        for raw_node in data.get("nodes", []):
            actions = []
            for raw_action in raw_node.get("actions", []):
                actions.append(Action(raw_action.get("type", "press"), raw_action.get("value")))
            loaded_nodes.append(Node(raw_node.get("name", "Node"), actions))

        self.nodes = loaded_nodes
        self.node_counter = len(self.nodes) + 1
        self.selected_node_index = 0 if self.nodes else None

        self.time_sleep_value = float(settings.get("time_sleep_value", 0.25))
        self.time_sleep_selector.setText(str(self.time_sleep_value))
        self.language_code = settings.get("language_code", self.language_code)
        self.change_theme(bool(settings.get("dark_mode", self.dark_mode)))
        self.csv_filename = settings.get("csv_filename")

        if self.csv_filename and os.path.exists(self.csv_filename):
            try:
                self.tabela = pd.read_csv(self.csv_filename)
                columns = [str(col) for col in self.tabela.columns]
                self.headers_combobox.clear()
                self.headers_combobox.addItems(columns)
                self.csv_fields_combobox.clear()
                self.csv_fields_combobox.addItems(columns)
            except Exception as exc:
                self.print_terminal(f"Falha ao recarregar CSV do projeto: {exc}")
        else:
            self.tabela = None

        self.update_ui_texts()
        self.update_node_list()
        self.update_preview_signal.emit()

    def save_project(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Save Project", "", "JSON Files (*.json)")
        if not filename:
            return
        try:
            with open(filename, "w", encoding="utf-8") as file:
                json.dump(self.nodes_to_dict(), file, ensure_ascii=False, indent=2)
            self.print_terminal(f"Projeto salvo em '{filename}'.")
        except Exception as exc:
            self.print_terminal(f"Erro ao salvar projeto: {exc}")

    def load_project(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Load Project", "", "JSON Files (*.json)")
        if not filename:
            return
        try:
            with open(filename, "r", encoding="utf-8") as file:
                data = json.load(file)
            self.snapshot_for_undo()
            self.load_project_from_dict(data)
            self.print_terminal(f"Projeto carregado de '{filename}'.")
        except Exception as exc:
            self.print_terminal(f"Erro ao carregar projeto: {exc}")

    def enable_csv_field_selection(self, state: int):
        enabled = state == 2
        self.csv_fields_combobox.setEnabled(enabled)
        self.csv_fields_combobox.clear()
        if enabled and self.tabela is not None:
            self.csv_fields_combobox.addItems([str(col) for col in self.tabela.columns])

    def start_record(self):
        if self.recording:
            self.print_terminal("Gravacao ja em andamento.")
            return
        if self.replaying:
            self.print_terminal("Pare a reproducao antes de gravar.")
            return

        self.recording = True
        self.record_paused = False
        self.current_actions = []
        self.last_record_click_position = None
        self.move_target_mode = False

        self.mouse_listener = MouseListener(on_click=self.on_click, on_scroll=self.on_scroll, on_move=self.on_move)
        self.keyboard_listener = KeyboardListener(on_press=self.on_press)
        self.mouse_listener.start()
        self.keyboard_listener.start()

        csv_columns = [str(col) for col in self.tabela.columns] if self.tabela is not None else []
        self.overlay.set_csv_columns(csv_columns)
        self.overlay.set_placeholder_status("Tip: click target field, then add placeholder")

        self.overlay.show()
        self.overlay.raise_()
        self.overlay.activateWindow()
        self.showMinimized()
        self.print_terminal(self.translate('Recording... Press "Stop" to finish.'))
        self.apply_mark_state("recording")

    def toggle_move_target_mode(self):
        if not self.recording:
            self.print_terminal("Inicie a gravacao para mover o target.")
            return
        if self.last_record_click_position is None:
            self.print_terminal("Defina um target com clique antes de mover.")
            return

        if not self.move_target_mode:
            self.move_target_mode = True
            self.was_paused_before_move = self.record_paused
            self.record_paused = True
            x, y = self.last_record_click_position
            self.target_marker_overlay.show_at(int(x), int(y), QColor("#ff9a6b"))
            self.overlay.set_placeholder_status("Move Target ativo: mova/click no texto; clique Move Target novamente para finalizar")
            self.print_terminal("Modo mover target ativo. Gravacao pausada automaticamente.")
        else:
            self.move_target_mode = False
            self.record_paused = self.was_paused_before_move
            self.target_marker_overlay.hide_marker()
            self.overlay.set_placeholder_status("Move Target finalizado")
            self.print_terminal("Modo mover target finalizado.")

    def add_csv_placeholder_action(self, column_name: str):
        if not self.recording:
            self.print_terminal("Inicie a gravacao para inserir placeholder CSV.")
            return
        if self.record_paused:
            self.print_terminal("Retome a gravacao antes de inserir placeholder CSV.")
            return
        if self.tabela is None:
            self.print_terminal("Importe um CSV antes de inserir placeholder.")
            return

        valid_columns = [str(col) for col in self.tabela.columns]
        if column_name not in valid_columns:
            self.print_terminal(f"Coluna CSV '{column_name}' nao encontrada.")
            return

        if self.last_record_click_position is None:
            self.print_terminal("Clique no campo de destino antes de adicionar o placeholder CSV.")
            self.overlay.set_placeholder_status("Click a target field first")
            return

        self.current_actions.append(Action("csv_placeholder", column_name))
        self.overlay.set_placeholder_status(f"Placeholder added: {column_name}")
        self.print_terminal(f"Placeholder CSV adicionado: {column_name}")
        x, y = self.last_record_click_position
        self.placeholder_pulse_overlay.flash(int(x), int(y), QColor("#7df0b3"))
        self.update_preview_signal.emit()

    def pause_resume_record(self):
        if not self.recording:
            self.print_terminal("Nenhuma gravacao ativa.")
            return
        if self.move_target_mode:
            self.print_terminal("Finalize o modo Move Target antes de pausar/retomar.")
            return
        self.record_paused = not self.record_paused
        self.print_terminal("Gravacao pausada." if self.record_paused else "Gravacao retomada.")
        self.apply_mark_state("record_paused" if self.record_paused else "recording")

    def stop_record(self):
        if self.replaying:
            self.stop_replay()
            self.print_terminal("Sinal de parada enviado para reproducao.")
            self.apply_mark_state("idle")
            return

        if not self.recording:
            return

        self.recording = False
        self.record_paused = False
        self.last_record_click_position = None
        self.move_target_mode = False
        self.target_marker_overlay.hide_marker()

        if self.mouse_listener is not None:
            self.mouse_listener.stop()
            self.mouse_listener = None
        if self.keyboard_listener is not None:
            self.keyboard_listener.stop()
            self.keyboard_listener = None

        self.overlay.hide()
        self.showNormal()

        if self.current_actions:
            self.snapshot_for_undo()
            node_name = f"Node {self.node_counter}"
            self.nodes.append(Node(name=node_name, actions=list(self.current_actions)))
            self.node_counter += 1
            self.print_terminal(f"{node_name} criado com {len(self.current_actions)} acoes.")
        else:
            self.print_terminal("Gravacao finalizada sem acoes.")

        self.current_actions = []
        self.update_node_list()
        self.update_preview_signal.emit()
        self.apply_mark_state("idle")

    def on_click(self, x, y, button, pressed):
        global_point = QPoint(int(x), int(y))

        def clicked_on_control_ui() -> bool:
            if self.overlay.isVisible() and self.overlay.frameGeometry().contains(global_point):
                return True
            if self.isVisible() and not self.isMinimized() and self.frameGeometry().contains(global_point):
                return True
            return False

        if not self.recording or self.record_paused or not pressed:
            if self.recording and self.move_target_mode and pressed:
                if clicked_on_control_ui():
                    return

                self.last_record_click_position = (x, y)
                self.target_marker_overlay.show_at(int(x), int(y), QColor("#7df0b3"))
                self.placeholder_pulse_overlay.flash(int(x), int(y), QColor("#7df0b3"))
                self.overlay.set_placeholder_status(f"Target preview: ({int(x)}, {int(y)})")
                self.print_terminal(f"Target atualizado para ({int(x)}, {int(y)}) em modo mover.")
            return

        if clicked_on_control_ui():
            return

        self.current_actions.append(Action("click", (x, y)))
        self.last_record_click_position = (x, y)
        self.overlay.set_placeholder_status(f"Target selected: ({int(x)}, {int(y)})")
        self.placeholder_pulse_overlay.flash(int(x), int(y), QColor("#ff6b6b"))
        self.update_preview_signal.emit()

    def on_move(self, x, y):
        if not self.recording or not self.move_target_mode:
            return

        now = time.time()
        if now - self.last_move_preview_ts < 0.016:
            return
        self.last_move_preview_ts = now

        self.last_record_click_position = (x, y)
        self.target_marker_overlay.show_at(int(x), int(y), QColor("#ff9a6b"))

    def on_scroll(self, x, y, dx, dy):
        if not self.recording or self.record_paused:
            return
        self.current_actions.append(Action("scroll", (dx, dy)))
        self.update_preview_signal.emit()

    def on_press(self, key):
        if not self.recording or self.record_paused:
            return
        try:
            if hasattr(key, "char") and key.char:
                self.current_actions.append(Action("press", key.char))
            elif key in [Key.ctrl, Key.shift, Key.alt, Key.cmd]:
                self.current_actions.append(Action("hotkey", key.name))
            else:
                self.current_actions.append(Action("press", getattr(key, "name", str(key))))
            self.update_preview_signal.emit()
        except Exception as exc:
            self.print_terminal(f"Erro ao registrar tecla: {exc}")

    def get_selected_node(self) -> Optional[Node]:
        if self.selected_node_index is None:
            return None
        if self.selected_node_index < 0 or self.selected_node_index >= len(self.nodes):
            return None
        return self.nodes[self.selected_node_index]

    def start_replay(self):
        if self.recording:
            self.print_terminal("Pare a gravacao antes de reproduzir.")
            return
        if self.replaying:
            self.print_terminal("Reproducao ja em andamento.")
            return

        selected = self.get_selected_node()
        nodes_to_replay = [selected] if selected else self.nodes
        if not nodes_to_replay:
            self.print_terminal("Nenhum node para reproduzir.")
            return

        self.replaying = True
        self.replay_paused = False
        self.stop_replay_event.clear()
        self.apply_mark_state("replaying")
        self.replay_thread = threading.Thread(target=self.replay, args=(nodes_to_replay,), daemon=True)
        self.replay_thread.start()

    def replay(self, nodes_to_replay: List[Node]):
        self.print_terminal("Reproducao iniciada.")
        repetition_count = self.repetition_lineedit.text().strip()
        total_iterations = int(repetition_count) if repetition_count.isdigit() and int(repetition_count) > 0 else 1

        has_csv_placeholders = any(
            action.action_type == "csv_placeholder"
            for node in nodes_to_replay
            for action in node.actions
        )

        if has_csv_placeholders:
            if self.tabela is None:
                self.print_terminal("Importe um CSV para executar placeholders.")
                self.replaying = False
                self.replay_paused = False
                self.apply_mark_state("idle")
                return
            if len(self.tabela.index) == 0:
                self.print_terminal("CSV sem linhas para preencher placeholders.")
                self.replaying = False
                self.replay_paused = False
                self.apply_mark_state("idle")
                return
            total_iterations = min(total_iterations, len(self.tabela.index))

        for iteration_index in range(total_iterations):
            if self.stop_replay_event.is_set():
                break

            row_data = self.tabela.iloc[iteration_index] if has_csv_placeholders and self.tabela is not None else None
            self.print_terminal(f"Iteracao {iteration_index + 1}/{total_iterations}")

            for node in nodes_to_replay:
                if self.stop_replay_event.is_set():
                    break
                self.print_terminal(f"Executando {node.name}...")

                for action in node.actions:
                    if self.stop_replay_event.is_set():
                        break
                    while self.replay_paused and not self.stop_replay_event.is_set():
                        time.sleep(0.1)

                    try:
                        if action.action_type == "click":
                            pyautogui.click(*action.value)
                        elif action.action_type == "press":
                            pyautogui.press(action.value)
                        elif action.action_type == "hotkey":
                            pyautogui.hotkey(action.value)
                        elif action.action_type == "scroll":
                            dy = action.value[1]
                            pyautogui.scroll(int(dy * 120))
                        elif action.action_type == "csv_placeholder":
                            if row_data is None:
                                raise ValueError("Sem linha CSV ativa para placeholder")
                            column_name = str(action.value)
                            if column_name not in row_data.index:
                                raise ValueError(f"Coluna '{column_name}' nao encontrada no CSV")
                            text_value = str(row_data[column_name])
                            pyautogui.write(text_value, interval=0.01)
                            self.print_terminal(
                                f"CSV -> {column_name} = '{text_value}' (iteracao {iteration_index + 1})"
                            )
                        time.sleep(self.time_sleep_value)
                    except Exception as exc:
                        self.print_terminal(f"Erro durante replay: {exc}")
                        self.stop_replay_event.set()
                        break

        self.replaying = False
        self.replay_paused = False
        self.print_terminal("Reproducao finalizada." if not self.stop_replay_event.is_set() else "Reproducao interrompida.")
        self.apply_mark_state("idle")

    def pause_resume_replay(self):
        if not self.replaying:
            self.print_terminal("Nenhuma reproducao ativa.")
            return
        self.replay_paused = not self.replay_paused
        self.print_terminal("Reproducao pausada." if self.replay_paused else "Reproducao retomada.")
        self.apply_mark_state("replay_paused" if self.replay_paused else "replaying")

    def stop_replay(self):
        if not self.replaying:
            return
        self.stop_replay_event.set()

    def import_csv(self):
        filename, _ = QFileDialog.getOpenFileName(self, self.translate("Import CSV"), "", "CSV Files (*.csv)")
        if not filename:
            return

        try:
            tabela = pd.read_csv(filename)
            self.tabela = tabela
            self.csv_filename = filename

            columns = [str(col) for col in tabela.columns]
            self.headers_combobox.clear()
            self.headers_combobox.addItems(columns)

            self.csv_fields_combobox.clear()
            self.csv_fields_combobox.addItems(columns)
            self.overlay.set_csv_columns(columns)

            self.print_terminal(self.translate("CSV file imported successfully."))
        except Exception as exc:
            self.print_terminal(f"{self.translate('Error importing CSV:')} {exc}")

    def export_actions(self):
        all_actions = [a for node in self.nodes for a in node.actions]
        if not all_actions:
            self.print_terminal(self.translate("No actions recorded to export."))
            return

        filename, _ = QFileDialog.getSaveFileName(self, self.translate("Export Actions"), "", "Text Files (*.txt)")
        if not filename:
            return

        with open(filename, "w", encoding="utf-8") as file:
            for node in self.nodes:
                file.write(f"[{node.name}]\n")
                for action in node.actions:
                    file.write(f"{action.action_type}: {action.value}\n")
                file.write("\n")
        self.print_terminal(f"Acoes exportadas para '{filename}'.")

    def clear_actions(self):
        self.stop_record()
        self.stop_replay()

        self.nodes.clear()
        self.current_actions.clear()
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.selected_node_index = None
        self.node_counter = 1
        self.is_updating_preview = False

        self.tabela = None
        self.csv_filename = None
        self.last_record_click_position = None
        self.move_target_mode = False
        self.headers_combobox.clear()
        self.csv_fields_combobox.clear()
        self.overlay.set_csv_columns([])
        self.overlay.set_placeholder_status("Tip: click target field, then add placeholder")
        self.target_marker_overlay.hide_marker()

        self.node_list.clear()
        self.code_preview.blockSignals(True)
        self.code_preview.clear()
        self.code_preview.blockSignals(False)
        self.terminal.clear()
        self.print_terminal("Tudo limpo com sucesso.")
        self.apply_mark_state("idle")

    def parse_preview_line(self, line: str) -> Action:
        parts = line.split(" ", 1)
        if len(parts) != 2:
            raise ValueError("Linha sem formato esperado: use '<acao> <valor>'")

        action_type = parts[0].strip().lower()
        raw_value = parts[1].strip()

        if action_type == "click":
            value = ast.literal_eval(raw_value)
            if not isinstance(value, tuple) or len(value) != 2:
                raise ValueError("click deve ser uma tupla (x, y)")
            return Action("click", (int(value[0]), int(value[1])))

        if action_type == "scroll":
            value = ast.literal_eval(raw_value)
            if not isinstance(value, tuple) or len(value) != 2:
                raise ValueError("scroll deve ser uma tupla (dx, dy)")
            return Action("scroll", (int(value[0]), int(value[1])))

        if action_type == "csv_placeholder":
            if raw_value.startswith(("'", '"')):
                raw_value = str(ast.literal_eval(raw_value))
            if not raw_value:
                raise ValueError("csv_placeholder sem coluna")
            return Action("csv_placeholder", raw_value)

        if action_type in ["press", "hotkey"]:
            if raw_value.startswith(("'", '"')):
                raw_value = str(ast.literal_eval(raw_value))
            if not raw_value:
                raise ValueError(f"{action_type} sem valor")
            return Action(action_type, raw_value)

        raise ValueError(f"Acao desconhecida: {action_type}")

    def generate_node_code(self):
        selected = self.get_selected_node()
        node = selected if selected else (self.nodes[0] if self.nodes else None)
        if node is None:
            self.print_terminal("Nenhum node para gerar codigo.")
            return

        repetition_count = self.repetition_lineedit.text().strip() or "1"
        if not repetition_count.isdigit():
            self.print_terminal("Contagem de repeticoes invalida.")
            return

        delay = self.time_sleep_value
        selected_header = self.headers_combobox.currentText().strip()

        filename, _ = QFileDialog.getSaveFileName(self, self.translate("Generate Node Code"), "", "Python Files (*.py)")
        if not filename:
            return

        lines = [
            "import time",
            "import pyautogui",
            "import pandas as pd",
            "",
            f"pyautogui.PAUSE = {delay}",
            "",
        ]

        if self.csv_filename and selected_header:
            lines.append(f"tabela = pd.read_csv(r'{self.csv_filename}')")
            lines.append(f"for _ in tabela['{selected_header}']:")
        else:
            lines.append(f"for _ in range({int(repetition_count)}):")

        for action in node.actions:
            if action.action_type == "click":
                x, y = action.value
                lines.append(f"    pyautogui.click({x}, {y})")
            elif action.action_type == "press":
                lines.append(f"    pyautogui.press('{action.value}')")
            elif action.action_type == "hotkey":
                lines.append(f"    pyautogui.hotkey('{action.value}')")
            elif action.action_type == "scroll":
                lines.append(f"    pyautogui.scroll({int(action.value[1] * 120)})")
            elif action.action_type == "csv_placeholder":
                if self.csv_filename:
                    lines.append(f"    pyautogui.write(str(_['{action.value}']))")
                else:
                    lines.append("    pyautogui.write('')")
            lines.append(f"    time.sleep({delay})")

        with open(filename, "w", encoding="utf-8") as file:
            file.write("\n".join(lines) + "\n")

        self.print_terminal(f"Codigo do node gerado em '{filename}'.")

    def edit_csv(self):
        if not self.csv_filename:
            self.print_terminal(self.translate("No CSV file imported."))
            return
        os.system(f'start excel "{self.csv_filename}"')
        self.print_terminal(self.translate("CSV file opened for editing."))

    def update_actions_from_code(self):
        if self.is_updating_preview:
            return

        node = self.get_selected_node()
        if node is None:
            return

        self.apply_mark_state("editing")

        lines = [line.strip() for line in self.code_preview.toPlainText().splitlines() if line.strip()]
        parsed: List[Action] = []
        parsing_errors = []

        for line_number, line in enumerate(lines, start=1):
            if line.startswith("#"):
                continue
            try:
                parsed.append(self.parse_preview_line(line))
            except Exception as exc:
                parsing_errors.append(f"linha {line_number}: {exc}")

        if parsing_errors:
            self.print_terminal("Preview com erro, alteracoes nao aplicadas: " + "; ".join(parsing_errors[:3]))
            return

        old_signature = [(a.action_type, a.value) for a in node.actions]
        new_signature = [(a.action_type, a.value) for a in parsed]
        if old_signature == new_signature:
            return

        self.snapshot_for_undo()
        node.actions = parsed
        self.update_node_list()

    def update_node_list(self):
        self.node_list.clear()
        for index, node in enumerate(self.nodes):
            self.node_list.addItem(f"{node.name} ({len(node.actions)} acoes)")
            if self.selected_node_index == index:
                self.node_list.setCurrentRow(index)

    def update_code_preview_from_node(self):
        row = self.node_list.currentRow()
        if row < 0 or row >= len(self.nodes):
            self.selected_node_index = None
            return

        self.selected_node_index = row
        self.update_preview_signal.emit()

    def update_preview_code(self):
        node = self.get_selected_node()
        actions = node.actions if node else self.current_actions

        preview_lines = []
        for action in actions:
            preview_lines.append(f"{action.action_type} {action.value}")

        self.is_updating_preview = True
        self.code_preview.blockSignals(True)
        self.code_preview.setPlainText("\n".join(preview_lines))
        self.code_preview.blockSignals(False)
        self.is_updating_preview = False

    def undo_action(self):
        if not self.undo_stack:
            return
        self.redo_stack.append(self.build_snapshot())
        self.restore_snapshot(self.undo_stack.pop())
        self.update_node_list()
        self.update_preview_signal.emit()
        self.print_terminal("Undo aplicado.")

    def redo_action(self):
        if not self.redo_stack:
            return
        self.undo_stack.append(self.build_snapshot())
        self.restore_snapshot(self.redo_stack.pop())
        self.update_node_list()
        self.update_preview_signal.emit()
        self.print_terminal("Redo aplicado.")

    def print_terminal(self, text: str):
        self.terminal.append(text)

    def change_theme(self, dark_mode: bool):
        self.dark_mode = dark_mode
        if self.dark_mode:
            self.setStyleSheet(
                """
                QMainWindow { background-color: #0f1412; color: #f1eadb; }
                QFrame#markHeader {
                    background-color: #141a17;
                    border: 1px solid #8f7a56;
                    border-radius: 10px;
                }
                QLabel#markTitle {
                    color: #d8be95;
                    font-size: 24px;
                    letter-spacing: 2px;
                    font-weight: 700;
                }
                QLabel#markSubtitle {
                    color: #8ea89c;
                    font-size: 11px;
                    letter-spacing: 1px;
                }
                QLabel#markStatusChip {
                    color: #102018;
                    background-color: #d8be95;
                    border-radius: 12px;
                    padding: 6px 12px;
                    font-weight: 700;
                }
                QFrame#markPanel {
                    background-color: #121917;
                    border: 1px solid #567f70;
                    border-radius: 12px;
                }
                QLabel#markPanelTitle {
                    color: #d8be95;
                    font-size: 12px;
                    letter-spacing: 1px;
                }
                QLabel#markQuote {
                    color: #d5d7ce;
                    font-size: 12px;
                }
                QLabel, QPushButton, QTextEdit, QListWidget, QComboBox, QLineEdit, QCheckBox {
                    color: #f2ece0;
                    background-color: #1a2320;
                    border: 1px solid #2d3d38;
                    border-radius: 8px;
                    padding: 6px;
                }
                QPushButton:hover {
                    background-color: #22302b;
                    border-color: #5f8c7b;
                }
                QPushButton:pressed {
                    background-color: #2a3a33;
                }
                QTextEdit#markEditor {
                    background-color: #121816;
                    border: 1px solid #5c846f;
                    font-family: Consolas;
                    font-size: 12px;
                }
                QMenuBar, QMenu, QMenu::item {
                    background-color: #141a17;
                    color: #efe8db;
                }
                QMenu::item:selected {
                    background-color: #2b3e38;
                }
                QScrollBar:vertical {
                    background: #111715;
                    width: 12px;
                    margin: 1px;
                }
                QScrollBar::handle:vertical {
                    background: #49685d;
                    min-height: 24px;
                    border-radius: 5px;
                }
                QScrollBar:horizontal {
                    background: #111715;
                    height: 12px;
                    margin: 1px;
                }
                QScrollBar::handle:horizontal {
                    background: #49685d;
                    min-width: 24px;
                    border-radius: 5px;
                }
                """
            )
        else:
            self.setStyleSheet(
                """
                QMainWindow { background-color: #ece8df; color: #1d2a24; }
                QFrame#markHeader {
                    background-color: #f5f1e9;
                    border: 1px solid #8b7d67;
                    border-radius: 10px;
                }
                QLabel#markTitle {
                    color: #2e433b;
                    font-size: 24px;
                    letter-spacing: 2px;
                    font-weight: 700;
                }
                QLabel#markSubtitle {
                    color: #577168;
                    font-size: 11px;
                    letter-spacing: 1px;
                }
                QLabel#markStatusChip {
                    color: #f5f1e9;
                    background-color: #30483f;
                    border-radius: 12px;
                    padding: 6px 12px;
                    font-weight: 700;
                }
                QFrame#markPanel {
                    background-color: #f4f0e8;
                    border: 1px solid #6f8d82;
                    border-radius: 12px;
                }
                QLabel#markPanelTitle {
                    color: #30483f;
                    font-size: 12px;
                    letter-spacing: 1px;
                }
                QLabel#markQuote {
                    color: #2b3a34;
                    font-size: 12px;
                }
                QLabel, QPushButton, QTextEdit, QListWidget, QComboBox, QLineEdit, QCheckBox {
                    color: #22312a;
                    background-color: #f8f4ec;
                    border: 1px solid #c6bda9;
                    border-radius: 8px;
                    padding: 6px;
                }
                QPushButton:hover {
                    background-color: #efe8dc;
                    border-color: #8aa093;
                }
                QPushButton:pressed {
                    background-color: #e4dbc9;
                }
                QTextEdit#markEditor {
                    background-color: #fcf8f1;
                    border: 1px solid #8aa093;
                    font-family: Consolas;
                    font-size: 12px;
                }
                QMenuBar, QMenu, QMenu::item {
                    background-color: #f5f1e9;
                    color: #22312a;
                }
                QMenu::item:selected {
                    background-color: #e0d9cb;
                }
                QScrollBar:vertical {
                    background: #ebe6da;
                    width: 12px;
                    margin: 1px;
                }
                QScrollBar::handle:vertical {
                    background: #8aa093;
                    min-height: 24px;
                    border-radius: 5px;
                }
                QScrollBar:horizontal {
                    background: #ebe6da;
                    height: 12px;
                    margin: 1px;
                }
                QScrollBar::handle:horizontal {
                    background: #8aa093;
                    min-width: 24px;
                    border-radius: 5px;
                }
                """
            )

    def set_font(self):
        font = QFont("Bahnschrift", 10)
        self.setFont(font)


def main():
    app = QApplication([])
    app.setStyle("Fusion")

    intro = MarkIntroDialog()
    intro.exec_()

    win = ActionRecorder()
    win.show()
    app.exec_()


if __name__ == "__main__":
    main()
