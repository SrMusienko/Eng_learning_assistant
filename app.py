from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import torch
import sounddevice as sd
from pathlib import Path
import queue
from threading import Thread

app = FastAPI()

class TextToSpeechPlayer:
    """ Класс для преобразования текста в речь """
    def __init__(self, model_path='v3_1_ru.pt', sample_rate=48000):
        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        # Load model
        self.device = torch.device('cpu')
        torch.set_num_threads(4)
        self.model = torch.package.PackageImporter(str(self.model_path)).load_pickle("tts_models", "model")
        self.model.to(self.device)
        
        # Queue for texts
        self.text_queue = queue.Queue()
        self.sample_rate = sample_rate
        self.is_running = False
        
        # Start playback thread
        self.playing_thread = Thread(target=self._play_thread, daemon=True)
        self.is_running = True
        self.playing_thread.start()
        
    def _play_thread(self):
        while self.is_running:
            try:
                text = self.text_queue.get()
                if text is None:
                    break
                # Generate audio
                audio = self.model.apply_tts(text=text,
                                          speaker='kseniya',
                                          sample_rate=self.sample_rate)
               
                # Play through speakers
                sd.play(audio, self.sample_rate)
                sd.wait()  # Wait for playback to finish
            except Exception as e:
                print(f"Playback error: {e}")
                
    def say(self, text):
        """Add text to the playback queue"""
        self.text_queue.put(text)
        
    def stop(self):
        """Stop playback and close thread"""
        self.is_running = False
        self.text_queue.put(None)
        self.playing_thread.join()

# Create an instance of TextToSpeechPlayer
tts_player = None

@app.on_event("startup")
async def startup_event():
    global tts_player
    try:
        tts_player = TextToSpeechPlayer()
    except Exception as e:
        print(f"Error initializing TTS: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    if tts_player:
        tts_player.stop()

@app.get("/", response_class=HTMLResponse)
async def get_home():
    html_content = """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Text-to-Speech Demo</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }
            textarea {
                width: 100%;
                height: 200px;
                margin-bottom: 10px;
                padding: 10px;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
            button {
                padding: 10px 15px;
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 16px;
            }
            button:hover {
                background-color: #45a049;
            }
            .checkbox-container {
                margin-bottom: 15px;
            }
            #status {
                margin-top: 10px;
                color: #666;
            }
        </style>
    </head>
    <body>
        <h1>Текст в речь</h1>
        
        <div class="checkbox-container">
            <input type="checkbox" id="enableSpeech" name="enableSpeech">
            <label for="enableSpeech">Озвучивать полученный текст</label>
        </div>
        
        <textarea id="textOutput" placeholder="Здесь будет отображаться полученный текст..."></textarea>
        
        <button id="getTextBtn">Получить текст</button>
        
        <div id="status"></div>
        
        <script>
            document.getElementById('getTextBtn').addEventListener('click', async () => {
                const statusElement = document.getElementById('status');
                const textareaElement = document.getElementById('textOutput');
                const enableSpeech = document.getElementById('enableSpeech').checked;
                
                statusElement.textContent = 'Получение текста...';
                
                try {
                    const response = await fetch('/get_text');
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    const data = await response.json();
                    
                    textareaElement.value = data.text;
                    statusElement.textContent = 'Текст получен!';
                    
                    if (enableSpeech) {
                        statusElement.textContent = 'Озвучивание текста...';
                        try {
                            await fetch('/speak_text', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                },
                                body: JSON.stringify({ text: data.text }),
                            });
                            statusElement.textContent = 'Текст озвучен!';
                        } catch (error) {
                            statusElement.textContent = `Ошибка озвучивания: ${error.message}`;
                        }
                    }
                } catch (error) {
                    statusElement.textContent = `Ошибка: ${error.message}`;
                }
            });
        </script>
    </body>
    </html>
    """
    return html_content

@app.get("/get_text")
async def get_text():
    # Здесь можно реализовать получение текста из вашего источника
    # Для примера возвращаем фиксированный текст
    return {"text": "Это пример текста, который будет преобразован в речь, если включен чекбокс."}

@app.post("/speak_text")
async def speak_text(request: Request):
    data = await request.json()
    text = data.get("text", "")
    
    if not text:
        return {"status": "error", "message": "Текст не предоставлен"}
    
    if tts_player:
        tts_player.say(text)
        return {"status": "success", "message": "Текст отправлен на озвучивание"}
    else:
        return {"status": "error", "message": "TTS система не инициализирована"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)