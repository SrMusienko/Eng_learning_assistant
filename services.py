import json
import queue
import asyncio
import uuid
import sqlite3
from pathlib import Path
from threading import Thread
from typing import Optional, Dict

import pyaudio
import sounddevice as sd
import torch
import torch.package
from vosk import Model, KaldiRecognizer
from llama_cpp import Llama
from pydantic import BaseModel

from logger_config import logger
import bcrypt

class SpeechRecognizer:
    """ !!!!!!!Class for converting speech to text!!!!!!!!!!!!!!"""
    def __init__(self, model_path, sample_rate=16000, frame_size=4000):
        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")
        self.sample_rate = sample_rate
        self.frame_size = frame_size
        self.model = Model(str(model_path))
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.is_running = False

    def open_stream(self):
        if self.stream is None or not self.stream.is_active():
            self.stream = self.audio.open(format=pyaudio.paInt16,
                                        channels=1,
                                        rate=self.sample_rate,
                                        input=True,
                                        frames_per_buffer=self.frame_size)
            self.stream.start_stream()
            logger.info('Audio stream opened.')

    def close_stream(self):
        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
            logger.info('Audio stream closed.')
        self.audio.terminate()  
        self.audio = pyaudio.PyAudio()  
        logger.info('Audio stream closed and reset.')

    async def recognize_stream(self, websocket):
        self.stop()
        self.open_stream()
        rec = KaldiRecognizer(self.model, self.sample_rate)
        rec.Reset() 
        self.is_running = True
        last_final_text = ""
        last_partial_text = ""

        try:
            while self.is_running:
                try:
                    data = self.stream.read(self.frame_size, exception_on_overflow=False)
                    if rec.AcceptWaveform(data):
                        result = json.loads(rec.Result())
                        if "text" in result and result["text"].strip():
                            current_text = result["text"]
                            if current_text != last_final_text:
                                await websocket.send_json({
                                    "type": "final",
                                    "text": current_text
                                })
                                last_final_text = current_text
                                last_partial_text = ""
                    else:
                        partial = json.loads(rec.PartialResult())
                        if "partial" in partial and partial["partial"].strip():
                            current_partial = partial["partial"]
                            if (current_partial != last_partial_text and 
                                current_partial != last_final_text):
                                await websocket.send_json({
                                    "type": "partial",
                                    "text": current_partial
                                })
                                last_partial_text = current_partial
                    
                    # Give other tasks a chance to run
                    await asyncio.sleep(0.01)
                except Exception as e:
                    logger.error(f"Error during recognition: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "text": f"Ошибка распознавания: {str(e)}"
                    })
                    break
        finally:
            self.close_stream()
            self.is_running = False

    def stop(self):
        self.is_running = False

class TextToSpeechPlayer:
    """ Text to speech class """
    def __init__(self, model_path=r'lang_models/v3_1_ru.pt', sample_rate=48000):
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

# LLM model for translations and explanations
class EnglishAssistant:
    """ Class for assistant """
    def __init__(self, model_path):
        self.llm = Llama(
            model_path=model_path,
            n_ctx=16384,
            n_gpu_layers=50
        )
        self.question = ""
        
    def process_request(self, text, native_lang, explanations):

        system_part=[
            f"You are an English learning assistant."
            f"The transcript is not perfect and may contain errors."
            f"You need to answer how correct the answer is."
            f"Answer as briefly as possible."
            f"Give your explanations in the language: {native_lang}."
            f"The words may be consonant then recognition will not understand it. But this is not a mistake."
        ]
        user_part= text
        # Add explanation requests
        if explanations:
            system_part.append("Also provide explanations for:")
            if "grammar" in explanations:
                system_part.append("- Grammar and tense usage")
            if "pronunciation" in explanations:
                system_part.append("- Pronunciation tips (in IPA notation)")
            if "alternatives" in explanations:
                system_part.append("- Alternative translation options or phrasings")
        

        # Get response from LLM
        response = self.llm.create_chat_completion(
            messages=[
                {"role": "system", "content": system_part},
                {"role": "assistant", "content": f"{self.question}"},
                {"role": "user", "content": user_part},
            ]
        )
        
        return response["choices"][0]["message"]["content"].strip()
    
    def get_native_responce(self, text_to_translate, native_lang):
        response = self.llm.create_chat_completion(
            messages=[
                {"role": "system", "content": 
                 f"""just a translation without any additional explanatory phrases,
                    only exclusively translation to {native_lang}"""
                },
                {"role": "user", "content": f"{text_to_translate}"},
            ]
        )
        self.llm.reset()
        return response
class DataManager:
    def __init__(self, db_path: str = "data/data.db", data_folder: str = "data"):
        self.db_path = db_path
        self.data_folder = data_folder
        self.files = {"question": "question.txt", "translation": "translation.txt"}
        self._init_db()
        self._update_db_from_files()
        self._reset_used()
        
    def _init_db(self) -> None:
        """Creates a table if it does not exist."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT CHECK(type IN ('question', 'translation')),
                level INTEGER CHECK(level BETWEEN 1 AND 10),
                text TEXT,
                used BOOLEAN DEFAULT 0
            )
        """)
        conn.commit()
        conn.close()

    def _reset_used(self) -> None:
        """Resets the used flag for all records."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("UPDATE entries SET used = 0")
        conn.commit()
        conn.close()
    
    def _update_db_from_files(self) -> None:
        """Updates the database if files have changed."""
        for entry_type, filename in self.files.items():
            path = self.data_folder / filename
            if path.exists():
                self._load_file_into_db(path, entry_type)
    
    def _load_file_into_db(self, filepath: str, entry_type: str) -> None:
        """Loads data from a file into a database."""
        with open(filepath, encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("DELETE FROM entries WHERE type = ?", (entry_type,))
        
        level = None
        for line in lines:
            if line.isdigit():
                level = int(line)
            else:
                cur.execute("INSERT INTO entries (type, level, text) VALUES (?, ?, ?)", (entry_type, level, line))
        
        conn.commit()
        conn.close()
    
    def get_next_entry(self, entry_type: str, level: int) -> Optional[str]:
        """Gets the next unused question/sentence."""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT id, text FROM entries WHERE type = ? AND level = ? AND used = 0 ORDER BY id LIMIT 1",
            (entry_type, level),
        )
        entry = cur.fetchone()
        
        if entry:
            entry_id, text = entry
            cur.execute("UPDATE entries SET used = 1 WHERE id = ?", (entry_id,))
            conn.commit()
            conn.close()
            return text
        else:
            conn.close()
            return None  # Все использованы
        
# Data Models
class User(BaseModel):
    id: str
    username: str
    email: str
    hashed_password: str
    settings: Dict = {}

class Token(BaseModel):
    access_token: str
    token_type: str

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

# Manage resources for each user
class UserResources:
    def __init__(self):
        self.resources = {}
    
    def get_or_create_resources(self, user_id: str):
        if user_id not in self.resources:
            self.resources[user_id] = {
                "tts_player": None,
                "speech_recognizer": None,
                "english_assistant": None,
            }
        return self.resources[user_id]
    
    def cleanup_resources(self, user_id: str):
        if user_id in self.resources:
            resources = self.resources[user_id]
            if resources["tts_player"]:
                resources["tts_player"].stop()
            self.resources.pop(user_id)

# Class for managing users
class UserManager:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.users_file = data_dir / "users.json"
        self.users = self._load_users()
        
    def _load_users(self):
        if not self.users_file.exists():
            self.users_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.users_file, "w") as f:
                json.dump({}, f)
            return {}
        
        with open(self.users_file, "r") as f:
            return json.load(f)
    
    def _save_users(self):
        with open(self.users_file, "w") as f:
            json.dump(self.users, f)
    
    def get_user_by_email(self, email: str):
        for user_id, user_data in self.users.items():
            if user_data["email"] == email:
                return User(
                    id=user_id,
                    username=user_data["username"],
                    email=user_data["email"],
                    hashed_password=user_data["hashed_password"],
                    settings=user_data.get("settings", {})
                )
        return None
    
    def get_user_by_id(self, user_id: str):
        if user_id in self.users:
            user_data = self.users[user_id]
            return User(
                id=user_id,
                username=user_data["username"],
                email=user_data["email"],
                hashed_password=user_data["hashed_password"],
                settings=user_data.get("settings", {})
            )
        return None
    
    def create_user(self, user_create: UserCreate):
        # Let's check that a user with this email does not already exist.
        if self.get_user_by_email(user_create.email):
            return None
        
        user_id = str(uuid.uuid4())
        hashed_password = hash_password(user_create.password)
        
        self.users[user_id] = {
            "username": user_create.username,
            "email": user_create.email,
            "hashed_password": hashed_password,
            "settings": {}
        }
        
        self._save_users()
        
        return User(
            id=user_id,
            username=user_create.username,
            email=user_create.email,
            hashed_password=hashed_password,
            settings={}
        )
    
    def update_user_settings(self, user_id: str, settings: Dict):
        if user_id in self.users:
            self.users[user_id]["settings"] = settings
            self._save_users()
            return True
        return False