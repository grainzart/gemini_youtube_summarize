# --- START OF FILE gemini_gui_app_pyqt.py ---

# Required libraries: PyQt6, google-generativeai, youtube-transcript-api

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

# --- CONSTANTS ---
PRESET_FILES = ["preset1.txt", "preset2.txt", "preset3.txt", "preset4.txt"]
API_KEY_FILE = "api_key.txt" # File to store the API key
# -----------------

# --- APPLICATION STYLESHEET ---
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

# --- Worker class for multithreading ---
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
            self.error.emit(f"An error occurred while contacting the API: {e}")

class GeminiGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.model = None # The model will be initialized later
        self.thread = None
        self.worker = None
        self._ensure_presets_exist()
        self._init_ui()
        self._load_and_init_api() # Attempt to load the key and initialize the API on startup

    def _init_ui(self):
        self.setWindowTitle("Gemini Youtube Summarize")
        self.setGeometry(100, 100, 800, 850)
        self.setStyleSheet(STYLESHEET)
        main_layout = QVBoxLayout(self)

        # --- API Settings Section ---
        api_group = QGroupBox("API Settings")
        api_layout = QHBoxLayout(api_group)
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("Paste your GOOGLE_API_KEY here")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password) # Hide the key
        self.save_api_key_button = QPushButton("Save and Apply")
        self.api_status_label = QLabel("Enter API key...")
        self.api_status_label.setObjectName("apiStatusLabel")
        api_layout.addWidget(QLabel("API Key:"))
        api_layout.addWidget(self.api_key_input)
        api_layout.addWidget(self.save_api_key_button)
        api_layout.addWidget(self.api_status_label)
        # ----------------------------

        # Other GUI sections
        presets_group = QGroupBox("Presets")
        presets_main_layout = QHBoxLayout(presets_group)
        for i, filename in enumerate(PRESET_FILES):
            preset_box = QVBoxLayout()
            label = QLabel(f"Preset {i+1}")
            label.setObjectName("presetLabel")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            buttons_layout = QHBoxLayout()
            load_button = QPushButton("Load")
            save_button = QPushButton("Save")
            load_button.clicked.connect(lambda checked, f=filename: self._load_preset(f))
            save_button.clicked.connect(lambda checked, f=filename: self._save_preset(f))
            buttons_layout.addWidget(load_button)
            buttons_layout.addWidget(save_button)
            preset_box.addWidget(label)
            preset_box.addLayout(buttons_layout)
            presets_main_layout.addLayout(preset_box)

        input_group = QGroupBox("Input Window")
        input_layout = QVBoxLayout(input_group)
        self.input_text = QTextEdit()
        self.input_text.setFixedHeight(150)
        self.send_button = QPushButton("Send (Ctrl+Enter)")
        input_layout.addWidget(self.input_text)
        input_layout.addWidget(self.send_button)
        
        youtube_group = QGroupBox("YouTube Link")
        youtube_layout = QVBoxLayout(youtube_group)
        self.youtube_link_input = QLineEdit()
        self.youtube_link_input.setPlaceholderText("Paste a YouTube video link here...")
        youtube_layout.addWidget(self.youtube_link_input)

        output_group = QGroupBox("Output Window")
        output_layout = QVBoxLayout(output_group)
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        output_layout.addWidget(self.output_text)

        console_group = QGroupBox("Console")
        console_layout = QVBoxLayout(console_group)
        self.console_text = QTextEdit()
        self.console_text.setReadOnly(True)
        self.console_text.setFixedHeight(150)
        self.console_text.setFont(QFont("Consolas", 9))
        self.console_text.setStyleSheet("background-color: black; color: lightgreen;")
        console_layout.addWidget(self.console_text)

        main_layout.addWidget(api_group) # Add the API section to the top
        main_layout.addWidget(presets_group)
        main_layout.addWidget(input_group)
        main_layout.addWidget(youtube_group)
        main_layout.addWidget(output_group)
        main_layout.addWidget(console_group)

        self.send_button.clicked.connect(self.send_prompt)
        self.send_button.setShortcut("Ctrl+Return")
        self.save_api_key_button.clicked.connect(self._save_and_init_api)

        self.log_to_console("Application started.")
        self._load_preset(PRESET_FILES[0])
        self._update_app_state(is_ready=False) # Initially, lock the application

    # --- Methods for handling the API key ---
    def _load_and_init_api(self):
        """Attempts to load the key from a file and initialize the API."""
        try:
            if os.path.exists(API_KEY_FILE):
                with open(API_KEY_FILE, 'r') as f:
                    api_key = f.read().strip()
                if api_key:
                    self.log_to_console("API key found in file, attempting initialization...")
                    self.api_key_input.setText(api_key)
                    self._try_init_model(api_key)
                else:
                    self.log_to_console("API key file is empty.")
            else:
                self.log_to_console(f"File '{API_KEY_FILE}' not found. Please enter the key manually.")
        except Exception as e:
            self.log_to_console(f"Error reading key file: {e}")

    def _save_and_init_api(self):
        """Saves the key from the input field and attempts to initialize the API."""
        api_key = self.api_key_input.text().strip()
        if not api_key:
            QMessageBox.warning(self, "Warning", "The API key field cannot be empty.")
            return
        
        try:
            with open(API_KEY_FILE, 'w') as f:
                f.write(api_key)
            self.log_to_console(f"API key saved to file '{API_KEY_FILE}'.")
            self._try_init_model(api_key)
        except Exception as e:
            self.log_to_console(f"Error saving key file: {e}")
            QMessageBox.critical(self, "File Error", f"Could not save the key file:\n{e}")

    def _try_init_model(self, api_key):
        """Core logic for model initialization."""
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash-lite')
            # Test request to validate the key
            self.model.generate_content("test", generation_config=genai.types.GenerationConfig(candidate_count=1))
            self.log_to_console(f"Model '{self.model.model_name}' initialized successfully.")
            self.api_status_label.setText("Key is active")
            self.api_status_label.setProperty("class", "success")
            self.api_status_label.style().polish(self.api_status_label)
            self._update_app_state(is_ready=True)
        except Exception as e:
            self.log_to_console(f"API initialization error: {e}")
            self.api_status_label.setText("Invalid key!")
            self.api_status_label.setProperty("class", "error")
            self.api_status_label.style().polish(self.api_status_label)
            self._update_app_state(is_ready=False)
            self.model = None

    def _update_app_state(self, is_ready: bool):
        """Enables or disables the main application functionality."""
        self.send_button.setEnabled(is_ready)
        self.input_text.setReadOnly(not is_ready)
        self.youtube_link_input.setReadOnly(not is_ready)
    # ------------------------------------------------

    def send_prompt(self):
        if not self.model:
            QMessageBox.critical(self, "Error", "Model is not initialized. Please check your API key.")
            return
        
        main_prompt = self.input_text.toPlainText().strip()
        youtube_url = self.youtube_link_input.text().strip()
        final_prompt = main_prompt

        if youtube_url:
            self.log_to_console(f"YouTube link detected: {youtube_url}")
            video_id = self._extract_video_id(youtube_url)
            if not video_id:
                QMessageBox.warning(self, "Error", "Could not extract video ID from the link. Please ensure the link is correct.")
                self.log_to_console("Error: Invalid YouTube link format.")
                return
            try:
                self.log_to_console(f"Fetching transcript for video ID: {video_id}...")
                self.display_output("⏳ Fetching YouTube transcript, please wait...")
                QApplication.processEvents()
                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['ru', 'en'])
                transcript_text = " ".join([item['text'] for item in transcript])
                self.log_to_console("Transcript successfully fetched. Merging with the main prompt.")
                final_prompt = f"{main_prompt}\n\n--- TRANSCRIPT FROM VIDEO ---\n{transcript_text}"
            except Exception as e:
                error_message = f"Could not fetch transcript: {e}"
                self.log_to_console(error_message)
                QMessageBox.critical(self, "YouTube Error", error_message)
                return
        
        if not final_prompt:
            QMessageBox.warning(self, "Warning", "The input field cannot be empty.")
            return
        
        self._update_app_state(is_ready=False) # Lock during the request
        self.display_output("⏳ Processing Gemini request, please wait...")
        self.log_to_console("Sending request to Gemini...")
        self.thread = QThread()
        self.worker = Worker(self.model, final_prompt)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_request_finished)
        self.worker.error.connect(self.on_request_error)
        self.thread.start()

    def cleanup_thread(self):
        self._update_app_state(is_ready=True) # Unlock after the request
        self.thread.quit()
        self.thread.wait()
        self.thread = None
        self.worker = None

    def _ensure_presets_exist(self):
        """Checks for preset files and creates them if they are missing."""
        for i, filename in enumerate(PRESET_FILES):
            if not os.path.exists(filename):
                try:
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(f"This is the text for preset #{i+1}. Edit this file.")
                except IOError as e:
                    QMessageBox.critical(self, "File Error", f"Could not create preset file {filename}:\n{e}")

    def _extract_video_id(self, url):
        """Extracts the 11-character video ID from various YouTube URL formats."""
        video_id = None
        if "watch?v=" in url:
            video_id = url.split("watch?v=")[1].split("&")[0]
        elif "youtu.be/" in url:
            video_id = url.split("youtu.be/")[1].split("?")[0]
        return video_id if video_id and len(video_id) == 11 else None

    def _format_model_output(self, text: str) -> str:
        """
        Cleans up list markers (* ) from the beginning of lines
        without affecting other formatting (bold text, line breaks).
        """
        # Replaces "* " at the beginning of each line with an empty string.
        # re.MULTILINE makes ^ match the start of each line.
        cleaned_text = re.sub(r'^\* ', '', text, flags=re.MULTILINE)
        return cleaned_text

    def on_request_finished(self, response_text):
        self.log_to_console("Response successfully received from API.")
        formatted_text = self._format_model_output(response_text)
        self.display_output(formatted_text)
        self.cleanup_thread()
    
    def on_request_error(self, error_message):
        self.log_to_console(error_message)
        self.display_output(f"❌ Error!\n\n{error_message}")
        self.cleanup_thread()
    
    def _load_preset(self, filename):
        """Loads text from a file into the input field."""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
            self.input_text.setPlainText(content)
            self.log_to_console(f"Preset '{filename}' loaded successfully.")
        except Exception as e:
            QMessageBox.critical(self, "File Error", f"Could not read file '{filename}':\n{e}")

    def _save_preset(self, filename):
        """Saves text from the input field to a file."""
        content = self.input_text.toPlainText()
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            self.log_to_console(f"Preset '{filename}' saved successfully.")
        except Exception as e:
            QMessageBox.critical(self, "File Error", f"Could not save file '{filename}':\n{e}")

    def log_to_console(self, message):
        now = datetime.now().strftime("%H:%M:%S")
        self.console_text.append(f"[{now}] {message}")

    def display_output(self, text):
        self.output_text.setPlainText(text)

if __name__ == '__main__':
    # The global try...except block is no longer needed here
    app = QApplication(sys.argv)
    window = GeminiGUI()
    window.show()
    sys.exit(app.exec())