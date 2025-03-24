from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
import json
import asyncio

import bcrypt
from jose import JWTError, jwt
import uvicorn

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates

from contextlib import asynccontextmanager

from logger_config import logger
from services import (SpeechRecognizer,
                      TextToSpeechPlayer,
                      EnglishAssistant,
                      DataManager,
                      UserManager,
                      UserCreate,
                      UserResources)
from services_create_templates import create_templates, update_index_template

SECRET_KEY = "YOUR_SECRET_KEY_HERE"  # В рабочем проекте это должно быть секретным
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # Токен на 24 часа

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

def authenticate_user(user_manager, email: str, password: str):
    user = user_manager.get_user_by_email(email)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = user_manager.get_user_by_id(user_id)
    if user is None:
        raise credentials_exception
    return user


BASE_DIR = Path(__file__).resolve().parent
INDEX_PATH = BASE_DIR / "templates" / "index.html"
LOGIN_PATH = BASE_DIR / "templates" / "login.html"
REGISTER_PATH = BASE_DIR / "templates" / "register.html"
MODEL_SPEECH_RECOGNIZER = "../models/vosk-model-small-en-us-zamia-0.5"
MODEL_SPEECH_PLAYER = BASE_DIR / "lang_models" / "v3_1_ru.pt"
MODEL_ENGLISH_ASSISTANT = "../models/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
TEMPLATES_DIR = BASE_DIR / "templates"

# Let's create directories if they don't exist yet.
TEMPLATES_DIR.mkdir(exist_ok=True)

#Create a resource and user manager
user_resources = UserResources()
user_manager = UserManager(BASE_DIR / "data")
data_manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global tts_player, speech_recognizer, english_assistant, data_manager

    tts_player = TextToSpeechPlayer(MODEL_SPEECH_PLAYER)
    speech_recognizer = SpeechRecognizer(MODEL_SPEECH_RECOGNIZER)
    english_assistant = EnglishAssistant(MODEL_ENGLISH_ASSISTANT)
    data_manager = DataManager(data_folder=BASE_DIR /"data" )
    yield
    if tts_player:
        tts_player.stop()

    for user_id in list(user_resources.resources.keys()):
        user_resources.cleanup_resources(user_id)

# Creating a FastAPI Application
app = FastAPI(title="English learner", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Calling creation/update of templates
create_templates()
update_index_template()


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(response: Response, form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(user_manager, form_data.username, form_data.password)
    if not user:
        return templates.TemplateResponse(
            "login.html", 
            {"request": {}, "error": "Incorrect email or password"}
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id}, expires_delta=access_token_expires
    )
    
    # Setting cookies with a token
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        expires=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )
    
    return response

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
):
    # Check that the passwords match
    if password != confirm_password:
        return templates.TemplateResponse(
            "register.html", 
            {"request": request, "error": "Passwords don't match"}
        )
    
    # Create a user
    user_create = UserCreate(username=username, email=email, password=password)
    user = user_manager.create_user(user_create)
    
    if not user:
        return templates.TemplateResponse(
            "register.html", 
            {"request": request, "error": "User with this email already exists"}
        )
    
    # Redirect to the login page
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/logout")
async def logout(response: Response):
    response = RedirectResponse(url="/login")
    response.delete_cookie("access_token")
    return response

# Function to get token from cookie
async def get_token_from_cookie(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    scheme, _, param = token.partition(" ")
    if scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme"
        )
    
    return param

# Function to get current user from cookie
async def get_current_user_from_cookie(request: Request):
    try:
        token = await get_token_from_cookie(request)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        user = user_manager.get_user_by_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        return user
    except (JWTError, HTTPException):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
# Global instances
tts_player = None
speech_recognizer = None
english_assistant = None
data_manager = None

@app.get("/", response_class=HTMLResponse)
async def get(request: Request):
    try:
        user = await get_current_user_from_cookie(request)
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            template_content = f.read()
        
        template_content = template_content.replace("{{ username }}", user.username)
        
        return HTMLResponse(content=template_content)
    except HTTPException:
        return RedirectResponse(url="/login")

@app.post("/save_settings")
async def save_settings(request: Request):
    try:
        user = await get_current_user_from_cookie(request)
        data = await request.json()
        
        settings = {
            "nativeLanguage": data.get("nativeLanguage"),
            "difficulty": data.get("difficulty"),
            "interactionType": data.get("interactionType"),
            "explanations": data.get("explanations", [])
        }
        
        success = user_manager.update_user_settings(user.id, settings)
        if success:
            return {"status": "success", "message": "Settings saved successfully"}
        else:
            return {"status": "error", "message": "Failed to save settings"}
    except HTTPException:
        return {"status": "error", "message": "Not authenticated"}

@app.get("/get_settings")
async def get_settings(request: Request):
    try:
        user = await get_current_user_from_cookie(request)
        return {"settings": user.settings}
    except HTTPException:
        return {"settings": {}}

@app.websocket("/ws/recognize")
async def websocket_endpoint(websocket: WebSocket):
    global speech_recognizer
    
    await websocket.accept()
    
    if speech_recognizer is None:
        try:
            speech_recognizer = SpeechRecognizer(MODEL_SPEECH_RECOGNIZER)
        except Exception as e:
            await websocket.send_json({"type": "error", "text": f"Initialization error: {str(e)}"})
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
    request: Request,
    text: str = Form(...),
    native_lang: str = Form(...),
    explanations: list = Form(None)
):
    try:
        user = await get_current_user_from_cookie(request)
        resources = user_resources.get_or_create_resources(user.id)
        
        if not resources["english_assistant"]:
            resources["english_assistant"] = EnglishAssistant(MODEL_ENGLISH_ASSISTANT)
        
        english_assistant = resources["english_assistant"]
        description = english_assistant.process_request(
            text,
            native_lang,
            explanations
        )
        
        return {"text": f"{description}"}
    except HTTPException:
        return {"text": "Authentication error. Please log in again."}


@app.post("/process")
async def process_text(
    request: Request,
    difficulty: int = Form(...),
    native_lang: str = Form(...),
    interaction_type: str = Form(...),
):
    try:
        user = await get_current_user_from_cookie(request)
        resources = user_resources.get_or_create_resources(user.id)
        
        tr_dic = {
            "Russian": "переведи на английский следующую фразу: ",
            "Ukrainian": "переклади англійською наступну фразу: ",
            "French": "traduisez la phrase suivante en anglais: "
        }
        qu_dic = {
            "Russian": "дай свой ответ на следующий вопрос: ",
            "Ukrainian": "дай свою відповідь на наступне запитання: ",
            "French": "donnez votre réponse à la question suivante: "
        }
        
        global data_manager
        if data_manager is None:
            data_manager = DataManager(data_folder=BASE_DIR / "data")
        
        text_to_translate = data_manager.get_next_entry(interaction_type, difficulty)
        text_to_translate = text_to_translate.rstrip('?')
        
        if not resources["english_assistant"]:
            resources["english_assistant"] = EnglishAssistant(MODEL_ENGLISH_ASSISTANT)
        
        english_assistant = resources["english_assistant"]
        response = english_assistant.get_native_responce(text_to_translate, native_lang)
        
        if interaction_type == "translation":
            result = tr_dic[native_lang] + response["choices"][0]["message"]["content"].strip()
        else: 
            result = qu_dic[native_lang] + response["choices"][0]["message"]["content"].strip() + "?"

        english_assistant.question = result
        
        user_manager.update_user_settings(user.id, {
            "nativeLanguage": native_lang,
            "difficulty": difficulty,
            "interactionType": interaction_type
        })
        
        return {"response": result}
    except HTTPException:
        return {"response": "Authentication error. Please log in again."}

@app.post("/speak_text")
async def speak_text(request: Request):
    try:
        user = await get_current_user_from_cookie(request)
        resources = user_resources.get_or_create_resources(user.id)
        
        data = await request.json()
        text = data.get("text", "")
        
        if not text:
            return {"status": "error", "message": "Текст не предоставлен"}
        
        if not resources["tts_player"]:
            resources["tts_player"] = TextToSpeechPlayer(MODEL_SPEECH_PLAYER)
        
        tts_player = resources["tts_player"]
        tts_player.say(text)
        
        return {"status": "success", "message": "Текст отправлен на озвучивание"}
    except HTTPException:
        return {"status": "error", "message": "Authentication error. Please log in again."}
    except Exception as e:
        return {"status": "error", "message": f"Ошибка инициализации или озвучивания: {e}"}
    
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
            