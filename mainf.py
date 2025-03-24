from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import json
import asyncio
from pathlib import Path
import uvicorn
from pathlib import Path
from fastapi import FastAPI, Request, Form, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI
from logger_config import logger
from services import SpeechRecognizer, TextToSpeechPlayer, EnglishAssistant, DataManager

BASE_DIR = Path(__file__).resolve().parent
INDEX_PATH = BASE_DIR / "templates" / "index.html"
MODEL_SPEECH_RECOGNIZER = "../models/vosk-model-small-en-us-zamia-0.5"
MODEL_SPEECH_PLAYER = BASE_DIR / "lang_models" / "v3_1_ru.pt"
MODEL_ENGLISH_ASSISTANT = "../models/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf" #Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"  #gemma-2-2b-it.Q8_0.gguf"

@asynccontextmanager
async def lifespan(app: FastAPI):
    global tts_player, speech_recognizer, english_assistant, data_manager
    
    # Инициализация ресурсов
    tts_player = TextToSpeechPlayer(MODEL_SPEECH_PLAYER)
    speech_recognizer = SpeechRecognizer(MODEL_SPEECH_RECOGNIZER)
    english_assistant = EnglishAssistant(MODEL_ENGLISH_ASSISTANT)
    data_manager = DataManager(data_folder=BASE_DIR /"data" )

    yield

    # Очистка ресурсов при завершении
    if tts_player:
        tts_player.stop()

app = FastAPI(title="English learner")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Global instances
tts_player = None
speech_recognizer = None
english_assistant = None
data_manager = None

@app.get("/", response_class=HTMLResponse)
async def get():
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        return f.read()


@app.websocket("/ws/recognize")
async def websocket_endpoint(websocket: WebSocket):
    global speech_recognizer
    
    await websocket.accept()
    
    if speech_recognizer is None:
        try:
            speech_recognizer = SpeechRecognizer(MODEL_SPEECH_RECOGNIZER)
        except Exception as e:
            await websocket.send_json({"type": "error", "text": f"Ошибка инициализации: {str(e)}"})
            await websocket.close()
            return
    
    try:
        # Stop any existing recognition process
        if speech_recognizer.is_running:
            speech_recognizer.stop()
        
        # Start recognition in a task
        recognition_task = asyncio.create_task(speech_recognizer.recognize_stream(websocket))
        
        # Listen for stop messages from client
        while True:
            try:
                msg = await websocket.receive_text()
                data = json.loads(msg)
                if data.get("action") == "stop":
                    speech_recognizer.stop()
                    break
            except WebSocketDisconnect:
                speech_recognizer.stop()
                break
            except Exception as e:
                logger.error(f"Error receiving message: {e}")
                break
                
        # Wait for recognition to complete
        await recognition_task

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
        if speech_recognizer:
            speech_recognizer.stop()
    except Exception as e:
        logger.error(f"Error in websocket endpoint: {e}")
        if speech_recognizer:
            speech_recognizer.stop()

@app.post("/get_anal")
async def get_anal(
    text: str = Form(...),
    native_lang: str = Form(...),
    explanations: list = Form(None)
):
    global english_assistant
    if english_assistant is None:
        english_assistant = EnglishAssistant(MODEL_ENGLISH_ASSISTANT)
    description = english_assistant.process_request(
        text,
        native_lang,
        explanations
    )
    return {"text": f"{description}"}

@app.post("/process")
async def process_text(
    difficulty: int = Form(...),
    native_lang: str = Form(...),
    interaction_type: str = Form(...),
):
    global english_assistant, data_manager
    tr_dic={
        "Russian": "переведи на английский следующую фразу: ",
        "Ukrainian": "переклади англійською наступну фразу: ",
        "French": "traduisez la phrase suivante en anglais: "
    }
    qu_dic={
        "Russian": "дай свой ответ на следующий вопрос: ",
        "Ukrainian": "дай свою відповідь на наступне запитання: ",
        "French": "donnez votre réponse à la question suivante: "
    }
    if data_manager is None:
        data_manager = DataManager(data_folder=BASE_DIR /"data" )
    text_to_translate = data_manager.get_next_entry(interaction_type,difficulty)
    text_to_translate = text_to_translate.rstrip('?')
    if english_assistant is None:
        english_assistant = EnglishAssistant(MODEL_ENGLISH_ASSISTANT)
    response = english_assistant.get_native_responce(text_to_translate, native_lang)
    if interaction_type == "translation":
        result =   tr_dic[native_lang]  + response["choices"][0]["message"]["content"].strip()
    else: 
        result =   qu_dic[native_lang]  + response["choices"][0]["message"]["content"].strip() + "?"

    english_assistant.question = result
    return {"response": result}

@app.post("/speak_text")
async def speak_text(request: Request):
    data = await request.json()
    text = data.get("text", "")
    
    if not text:
        return {"status": "error", "message": "Текст не предоставлен"}
    
    try:

        tts_player.say(text)
        tts_player.stop()  
        return {"status": "success", "message": "Текст отправлен на озвучивание"}
    except Exception as e:
        return {"status": "error", "message": f"Ошибка инициализации или озвучивания: {e}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)