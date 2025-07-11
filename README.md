# Gemini Youtube Summarize Tool

**Gemini GUI** is a desktop application that provides a user-friendly graphical interface for interacting with Google's powerful Gemini language models. Analyze text, summarize YouTube videos, and automate routine tasks with customizable prompt presets.

![Image](https://github.com/user-attachments/assets/c0070601-b1b4-4af8-a6a2-c31f2739385a)

## ✨ Key Features

*   **Direct Access to Gemini:** Interact with `gemini-2.0-flash-lite` directly from your desktop.
*   **YouTube Video Analysis:** Simply paste a video link, and the app will automatically fetch the subtitles for the model to analyze.
*   **Customizable Presets:** Create, save, and load your own prompt templates for frequently used tasks. Presets are stored in plain `.txt` files for easy editing.
*   **Secure API Key Storage:** Your API key is stored locally in an `api_key.txt` file and is never committed to the repository.
*   **Cross-Platform:** The application is built to run on Windows, macOS, and Linux.
*   **Dark Theme:** A comfortable and modern user interface.

## 🚀 Installation and Usage

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/grainzart/gemini_youtube_summarize.git
    cd gemini_youtube_summarize
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    # For venv
    python -m venv env
    source env/bin/activate  # On Windows: env\Scripts\activate

    # Or for Conda
    conda create --name gemini_gui python=3.11
    conda activate gemini_gui
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Create the API key file:**
    Create a file named `api_key.txt` in the project root and paste your Google AI API key into it.
    Or use GUI to paste your key.

5.  **Run the application:**
    ```bash
    python gemini_gui_app.py
    ```

## 🛠️ How to Use

1.  **Set Up Your API Key:** On first launch, enter your key in the top input field and save it. The "Key is active" status will confirm that everything is working.
2.  **Use Presets:**
    *   Click **"Load"** to insert a prompt template into the main input window.
    *   Edit the prompt and click **"Save"** to update the corresponding `.txt` file.
3.  **Analyze a YouTube Video:**
    *   Paste a video link into the dedicated field.
    *   In the main input window, write what you want the model to do with the video's transcript (e.g., "Summarize this video.").
    *   Click "Send".
4.  **Send a Request:** Write your query in the "Input Window" and click **"Send"** or press `Ctrl+Enter`.

