# English Learning Assistant

This project is an English learning assistant that provides interactive tools to help users improve their English language skills. It offers features such as speech recognition, text-to-speech, translation, questions and answers, and detailed explanations of grammar, pronunciation, and alternative translations.

## Features

-   **Speech Recognition:** Allows users to speak and have their speech converted into text.
-   **Text-to-Speech:** Reads out text to help users with pronunciation and listening skills.
-   **Translation:** Translates phrases from the user's native language to English.
-   **Questions & Answers:** Provides interactive questions and answers to enhance comprehension.
-   **Detailed Explanations:** Offers explanations on grammar, pronunciation, and alternative translations.
-   **User Settings:** Allows users to customize their learning experience by setting their native language, difficulty level, and interaction type.
-   **User Authentication:** Secure user authentication with login and registration.
-   **Persistent Settings:** User settings are saved and loaded upon login.
-   **Dynamic Content:** Content is dynamically generated based on user preferences and progress.

## Technologies Used

-   **FastAPI:** A modern, fast (high-performance), web framework for building APIs with Python 3.7+ based on standard Python type hints.
-   **Vosk:** A speech recognition toolkit that supports multiple languages.
-   **TTS (Text-to-Speech):** Used for converting text to speech.
-   **Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf:** Language model for generating responses and translations.
-   **Jinja2:** A modern and designer-friendly templating language for Python.
-   **bcrypt:** Password hashing function.
-   **jose:** JSON Object Signing and Encryption library.
-   **uvicorn:** ASGI web server.
-   **HTML/CSS/JavaScript:** For the frontend interface.
-   **WebSockets:** For real-time speech recognition.

## Setup

1.  **Clone the repository:**

    ```bash
    git clone <repository_url>
    cd english-learning-assistant
    ```

2.  **Create a virtual environment (recommended):**

    ```bash
    python -m venv venv
    source venv/bin/activate  # On macOS and Linux
    venv\Scripts\activate  # On Windows
    ```

3.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Download necessary models:**

    -   Download the Vosk speech recognition model (`vosk-model-small-en-us-zamia-0.5`) and place it in the `models` directory.
    -   Download the TTS model (`v3_1_ru.pt`) and place it in the `lang_models` directory.
    -   Download the Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf language model and place it in the `models` directory.

5.  **Set the `SECRET_KEY`:**

    -   Replace `"YOUR_SECRET_KEY_HERE"` in the `main.py` file with a secure random key.

6.  **Run the application:**

    ```bash
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
    ```

7.  **Access the application:**

    -   Open your web browser and navigate to `http://0.0.0.0:8000`.

## Project Structure
'''
english-learning-assistant/
├── main.py             # Main FastAPI application
├── services.py         # Backend services (speech recognition, TTS, etc.)
├── services_create_templates.py # Script for creating/updating html templates
├── templates/          # HTML templates
│   ├── index.html
│   ├── login.html
│   ├── register.html
├── static/             # Static files (CSS, JavaScript, images)
├── models/             # Speech recognition and language models
│   ├── vosk-model-small-en-us-zamia-0.5
│   ├── Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf
├── lang_models/        # TTS models
│   ├── v3_1_ru.pt
├── data/               # User data and settings
├── requirements.txt    # Project dependencies
├── logger_config.py    # Logger configuration
└── README.md           # Project documentation
'''
## Usage

1.  **Register or log in:**
    -   Create a new account or log in with existing credentials.
    ![login](/static/images/6.png)![register](/static/images/7.png)
2.  **Customize settings:**
    -   Click the settings icon to adjust your native language, difficulty level, and interaction type.
    ![step1](/static/images/2.png)
3.  **Get queestion from LLM**
    -   Click the button "Lets start".
    ![step2](/static/images/3.png)
4.  **Use speech recognition to answer the question:**
    -   Click the microphone icon to start recording your speech.
    ![step3](/static/images/4.png)
5.  **Receive assistant responses:**
    -   The assistant will provide responses based on your settings and input.
    ![step4](/static/images/5.png)
6.  **Listen to text:**
    -   Enable the voice feature to have the assistant's responses read aloud.

## Future Improvements

-   Implement more advanced language models for better responses.
-   Add support for more languages.
-   Improve the user interface and user experience.
-   Incorporate more interactive learning exercises.
-   Add progress tracking and analytics.
-   Implement a database for persistent storage of user data and learning progress.
