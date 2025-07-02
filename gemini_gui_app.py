# --- START OF FILE gemini_gui_app_pyqt.py ---

# Установленные библиотеки: PyQt6, google-generativeai, youtube-transcript-api

import sys
import os
import threading
from datetime import datetime
import re

from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
                             QTextEdit, QPushButton, QMessageBox, QLabel, QLineEdit) 
from PyQt6.QtCore import QObject, pyqtSignal, QThread, Qt
from PyQt6.QtGui import QFont

import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi

# --- КОНСТАНТЫ ---
PRESET_FILES = ["preset1.txt", "preset2.txt", "preset3.txt", "preset4.txt"]
API_KEY_FILE = "api_key.txt" # Файл для хранения ключа
# -----------------

# --- СТИЛЬ ПРИЛОЖЕНИЯ (без изменений) ---
STYLESHEET = """
    QWidget {
        background-color: #2E2E2E;
        color: #EAEAEA;
        font-family: "Segoe UI";
        font-size: 10pt;
    }
    QGroupBox {
        font-weight: bold;
        border: 1px solid #555555;
        border-radius: 5px;
        margin-top: 1ex;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 3px;
    }
    QTextEdit, QLineEdit {
        background-color: #3C3C3C;
        border: 1px solid #555555;
        border-radius: 3px;
    }
    QLineEdit {
        padding: 4px;
        font-size: 11pt;
    }
    QPushButton {
        background-color: #555555;
        border: none;
        padding: 5px 10px;
        border-radius: 4px;
    }
    QPushButton:hover {
        background-color: #666666;
    }
    QPushButton:pressed {
        background-color: #444444;
    }
    QPushButton:disabled {
        background-color: #404040;
        color: #888888;
    }
    QLabel#presetLabel {
        font-weight: bold;
    }
    QLabel#apiStatusLabel.success {
        color: lightgreen;
    }
    QLabel#apiStatusLabel.error {
        color: #FF7777;
    }
"""

# --- Класс Worker для многопоточности (без изменений) ---
class Worker(QObject):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    def __init__(self, model, prompt):
        super().__init__()
        self.model = model
        self.prompt = prompt
    def run(self):
        try:
            response = self.model.generate_content(self.prompt)
            self.finished.emit(response.text)
        except Exception as e:
            self.error.emit(f"Произошла ошибка при обращении к API: {e}")

class GeminiGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.model = None # Модель будет инициализирована позже
        self.thread = None
        self.worker = None
        self._ensure_presets_exist()
        self._init_ui()
        self._load_and_init_api() # Пытаемся загрузить ключ и запустить API при старте

    def _init_ui(self):
        self.setWindowTitle("Gemini GUI (PyQt6)")
        self.setGeometry(100, 100, 800, 850)
        self.setStyleSheet(STYLESHEET)
        main_layout = QVBoxLayout(self)

        # --- НОВЫЙ БЛОК: Настройки API ---
        api_group = QGroupBox("Настройки API")
        api_layout = QHBoxLayout(api_group)
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("Вставьте ваш GOOGLE_API_KEY сюда")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password) # Скрываем ключ
        self.save_api_key_button = QPushButton("Сохранить и применить")
        self.api_status_label = QLabel("Введите API ключ...")
        self.api_status_label.setObjectName("apiStatusLabel")
        api_layout.addWidget(QLabel("API Ключ:"))
        api_layout.addWidget(self.api_key_input)
        api_layout.addWidget(self.save_api_key_button)
        api_layout.addWidget(self.api_status_label)
        # ------------------------------------

        # Остальные секции GUI
        presets_group = QGroupBox("Пресеты")
        presets_main_layout = QHBoxLayout(presets_group)
        for i, filename in enumerate(PRESET_FILES):
            preset_box = QVBoxLayout()
            label = QLabel(f"Пресет {i+1}")
            label.setObjectName("presetLabel")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            buttons_layout = QHBoxLayout()
            load_button = QPushButton("Загрузить")
            save_button = QPushButton("Сохранить")
            load_button.clicked.connect(lambda checked, f=filename: self._load_preset(f))
            save_button.clicked.connect(lambda checked, f=filename: self._save_preset(f))
            buttons_layout.addWidget(load_button)
            buttons_layout.addWidget(save_button)
            preset_box.addWidget(label)
            preset_box.addLayout(buttons_layout)
            presets_main_layout.addLayout(preset_box)

        input_group = QGroupBox("Окно ввода")
        input_layout = QVBoxLayout(input_group)
        self.input_text = QTextEdit()
        self.input_text.setFixedHeight(150)
        self.send_button = QPushButton("Отправить (Ctrl+Enter)")
        input_layout.addWidget(self.input_text)
        input_layout.addWidget(self.send_button)
        
        youtube_group = QGroupBox("Ссылка на YouTube")
        youtube_layout = QVBoxLayout(youtube_group)
        self.youtube_link_input = QLineEdit()
        self.youtube_link_input.setPlaceholderText("Вставьте ссылку на YouTube видео сюда...")
        youtube_layout.addWidget(self.youtube_link_input)

        output_group = QGroupBox("Окно вывода")
        output_layout = QVBoxLayout(output_group)
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        output_layout.addWidget(self.output_text)

        console_group = QGroupBox("Консоль")
        console_layout = QVBoxLayout(console_group)
        self.console_text = QTextEdit()
        self.console_text.setReadOnly(True)
        self.console_text.setFixedHeight(150)
        self.console_text.setFont(QFont("Consolas", 9))
        self.console_text.setStyleSheet("background-color: black; color: lightgreen;")
        console_layout.addWidget(self.console_text)

        main_layout.addWidget(api_group) # Добавляем секцию API наверх
        main_layout.addWidget(presets_group)
        main_layout.addWidget(input_group)
        main_layout.addWidget(youtube_group)
        main_layout.addWidget(output_group)
        main_layout.addWidget(console_group)

        self.send_button.clicked.connect(self.send_prompt)
        self.send_button.setShortcut("Ctrl+Return")
        self.save_api_key_button.clicked.connect(self._save_and_init_api)

        self.log_to_console("Приложение запущено.")
        self._load_preset(PRESET_FILES[0])
        self._update_app_state(is_ready=False) # Изначально блокируем приложение

    # --- НОВЫЕ МЕТОДЫ для работы с API ключом ---
    def _load_and_init_api(self):
        """Пытается загрузить ключ из файла и инициализировать API."""
        try:
            if os.path.exists(API_KEY_FILE):
                with open(API_KEY_FILE, 'r') as f:
                    api_key = f.read().strip()
                if api_key:
                    self.log_to_console("API ключ найден в файле, попытка инициализации...")
                    self.api_key_input.setText(api_key)
                    self._try_init_model(api_key)
                else:
                    self.log_to_console("Файл с API ключом пуст.")
            else:
                self.log_to_console(f"Файл '{API_KEY_FILE}' не найден. Введите ключ вручную.")
        except Exception as e:
            self.log_to_console(f"Ошибка при чтении файла с ключом: {e}")

    def _save_and_init_api(self):
        """Сохраняет ключ из поля ввода и пытается инициализировать API."""
        api_key = self.api_key_input.text().strip()
        if not api_key:
            QMessageBox.warning(self, "Внимание", "Поле API ключа не может быть пустым.")
            return
        
        try:
            with open(API_KEY_FILE, 'w') as f:
                f.write(api_key)
            self.log_to_console(f"API ключ сохранен в файл '{API_KEY_FILE}'.")
            self._try_init_model(api_key)
        except Exception as e:
            self.log_to_console(f"Ошибка при сохранении файла с ключом: {e}")
            QMessageBox.critical(self, "Ошибка файла", f"Не удалось сохранить файл с ключом:\n{e}")

    def _try_init_model(self, api_key):
        """Основная логика инициализации модели."""
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash-lite')
            # Пробный запрос для проверки ключа
            self.model.generate_content("test", generation_config=genai.types.GenerationConfig(candidate_count=1))
            self.log_to_console(f"Модель '{self.model.model_name}' успешно инициализирована.")
            self.api_status_label.setText("Ключ активен")
            self.api_status_label.setProperty("class", "success")
            self.api_status_label.style().polish(self.api_status_label)
            self._update_app_state(is_ready=True)
        except Exception as e:
            self.log_to_console(f"Ошибка инициализации API: {e}")
            self.api_status_label.setText("Ошибка ключа!")
            self.api_status_label.setProperty("class", "error")
            self.api_status_label.style().polish(self.api_status_label)
            self._update_app_state(is_ready=False)
            self.model = None

    def _update_app_state(self, is_ready: bool):
        """Включает или выключает основную функциональность приложения."""
        self.send_button.setEnabled(is_ready)
        self.input_text.setReadOnly(not is_ready)
        self.youtube_link_input.setReadOnly(not is_ready)
    # ------------------------------------------------

    def send_prompt(self):
        if not self.model:
            QMessageBox.critical(self, "Ошибка", "Модель не инициализирована. Проверьте ваш API ключ.")
            return
        
        # ... (остальная логика send_prompt без изменений) ...
        main_prompt = self.input_text.toPlainText().strip()
        youtube_url = self.youtube_link_input.text().strip()
        final_prompt = main_prompt
        if youtube_url:
            self.log_to_console(f"Обнаружена ссылка на YouTube: {youtube_url}")
            video_id = self._extract_video_id(youtube_url)
            if not video_id:
                QMessageBox.warning(self, "Ошибка", "Не удалось извлечь ID видео из ссылки. Убедитесь, что ссылка корректна.")
                self.log_to_console("Ошибка: неверный формат ссылки YouTube.")
                return
            try:
                self.log_to_console(f"Получение субтитров для видео ID: {video_id}...")
                self.display_output("⏳ Получение субтитров из YouTube, пожалуйста, подождите...")
                QApplication.processEvents()
                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['ru', 'en'])
                transcript_text = " ".join([item['text'] for item in transcript])
                self.log_to_console("Субтитры успешно получены. Объединение с основным промптом.")
                final_prompt = f"{main_prompt}\n\n--- ТЕКСТ СУБТИТРОВ ИЗ ВИДЕО ---\n\n{transcript_text}"
            except Exception as e:
                error_message = f"Не удалось получить субтитры: {e}"
                self.log_to_console(error_message)
                QMessageBox.critical(self, "Ошибка YouTube", error_message)
                return
        if not final_prompt:
            QMessageBox.warning(self, "Внимание", "Поле ввода не может быть пустым.")
            return
        self._update_app_state(is_ready=False) # Блокируем на время запроса
        self.display_output("⏳ Обработка запроса Gemini, пожалуйста, подождите...")
        self.log_to_console("Отправка запроса Gemini...")
        self.thread = QThread()
        self.worker = Worker(self.model, final_prompt)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_request_finished)
        self.worker.error.connect(self.on_request_error)
        self.thread.start()

    def cleanup_thread(self):
        self._update_app_state(is_ready=True) # Разблокируем после запроса
        self.thread.quit()
        self.thread.wait()
        self.thread = None
        self.worker = None

    # ... (все остальные методы остаются без изменений) ...
    def _ensure_presets_exist(self):
        for i, filename in enumerate(PRESET_FILES):
            if not os.path.exists(filename):
                try:
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(f"Это текст для пресета №{i+1}. Отредактируйте этот файл.")
                except IOError as e:
                    QMessageBox.critical(self, "Ошибка файла", f"Не удалось создать файл пресета {filename}:\n{e}")

    def _extract_video_id(self, url):
        video_id = None
        if "watch?v=" in url:
            video_id = url.split("watch?v=")[1].split("&")[0]
        elif "youtu.be/" in url:
            video_id = url.split("youtu.be/")[1].split("?")[0]
        return video_id if video_id and len(video_id) == 11 else None

    def _format_model_output(self, text: str) -> str:
        cleaned_text = re.sub(r'^\* ', '', text, flags=re.MULTILINE)
        return cleaned_text

    def on_request_finished(self, response_text):
        self.log_to_console("Ответ от API успешно получен.")
        formatted_text = self._format_model_output(response_text)
        self.display_output(formatted_text)
        self.cleanup_thread()
    
    def on_request_error(self, error_message):
        self.log_to_console(error_message)
        self.display_output(f"❌ Ошибка!\n\n{error_message}")
        self.cleanup_thread()
    
    def _load_preset(self, filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
            self.input_text.setPlainText(content)
            self.log_to_console(f"Пресет '{filename}' успешно загружен.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка файла", f"Не удалось прочитать файл '{filename}':\n{e}")

    def _save_preset(self, filename):
        content = self.input_text.toPlainText()
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            self.log_to_console(f"Пресет '{filename}' успешно сохранен.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка файла", f"Не удалось сохранить файл '{filename}':\n{e}")

    def log_to_console(self, message):
        now = datetime.now().strftime("%H:%M:%S")
        self.console_text.append(f"[{now}] {message}")

    def display_output(self, text):
        self.output_text.setPlainText(text)

if __name__ == '__main__':
    # Убираем глобальный блок try...except
    app = QApplication(sys.argv)
    window = GeminiGUI()
    window.show()
    sys.exit(app.exec())