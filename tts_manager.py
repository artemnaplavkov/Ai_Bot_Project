import os
import hashlib
import threading
import queue
import time
from pathlib import Path
from TTS.api import TTS
import playsound
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TTSManager:
    
    def __init__(self, model_name: str = "tts_models/ru/multilingual/v3", cache_dir: str = "tts_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        self.model_name = model_name
        self.tts = None
        self.speech_queue = queue.Queue()
        self.worker_thread = None
        self.running = False
        
        self._load_model()
        self._start_worker()
        
        logger.info(f"TTS Manager инициализирован. Модель: {model_name}")
    
    def _load_model(self):
        try:
            logger.info(f"Загрузка модели TTS: {self.model_name}...")
            self.tts = TTS(model_name=self.model_name, progress_bar=False)
            logger.info("Модель TTS успешно загружена")
        except Exception as e:
            logger.error(f"Ошибка загрузки модели TTS: {e}")
            logger.info("Пробуем загрузить английскую модель как fallback...")
            try:
                self.tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC", progress_bar=False)
                logger.info("Английская модель загружена (fallback)")
            except Exception as e2:
                logger.error(f"Не удалось загрузить ни одну модель TTS: {e2}")
                self.tts = None
    
    def _get_cache_path(self, text: str) -> Path:
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        return self.cache_dir / f"{text_hash}.wav"
    
    def _normalize_text(self, text: str) -> str:
        replacements = {
            '°C': 'градусов цельсия',
            'км/ч': 'километров в час',
            '+': 'плюс',
            '=': 'равно',
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        numbers = {
            '0': 'ноль', '1': 'один', '2': 'два', '3': 'три', '4': 'четыре',
            '5': 'пять', '6': 'шесть', '7': 'семь', '8': 'восемь', '9': 'девять',
            '10': 'десять', '11': 'одиннадцать', '12': 'двенадцать', '13': 'тринадцать',
            '14': 'четырнадцать', '15': 'пятнадцать', '16': 'шестнадцать',
            '17': 'семнадцать', '18': 'восемнадцать', '19': 'девятнадцать',
            '20': 'двадцать', '30': 'тридцать', '40': 'сорок', '50': 'пятьдесят', '100': 'сто'
        }
        
        words = text.split()
        normalized_words = []
        for word in words:
            if word.isdigit() and word in numbers:
                normalized_words.append(numbers[word])
            else:
                normalized_words.append(word)
        
        return ' '.join(normalized_words)
    
    def speak(self, text: str, block: bool = False):
        if self.tts is None:
            logger.warning("TTS не доступен")
            return
        
        if not text or not text.strip():
            return
        
        normalized_text = self._normalize_text(text)
        
        if block:
            self._generate_and_play(normalized_text)
        else:
            self.speech_queue.put(normalized_text)
    
    def _generate_and_play(self, text: str):
        try:
            cache_path = self._get_cache_path(text)
            
            if cache_path.exists():
                logger.debug(f"Используем кэш: {cache_path.name}")
                audio_path = str(cache_path)
            else:
                logger.debug(f"Синтезируем речь: {text[:50]}...")
                self.tts.tts_to_file(text=text, file_path=str(cache_path))
                audio_path = str(cache_path)
                logger.debug(f"Аудио сохранено в кэш: {cache_path.name}")
            
            playsound.playsound(audio_path)
            
        except Exception as e:
            logger.error(f"Ошибка при озвучивании: {e}")
    
    def _start_worker(self):
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
    
    def _worker_loop(self):
        while self.running:
            try:
                text = self.speech_queue.get(timeout=0.5)
                self._generate_and_play(text)
                self.speech_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Ошибка в worker: {e}")
    
    def wait_for_completion(self):
        self.speech_queue.join()
    
    def shutdown(self):
        logger.info("Завершение работы TTS Manager...")
        self.running = False
        if self.worker_thread and self.worker_thread.is_alive():
            self.wait_for_completion()
        logger.info("TTS Manager остановлен")
    
    def get_cache_size(self) -> int:
        return len(list(self.cache_dir.glob("*.wav")))
    
    def clear_cache(self):
        for file in self.cache_dir.glob("*.wav"):
            file.unlink()
        logger.info(f"Кэш очищен. Удалено файлов: {self.get_cache_size()}")


_tts_manager = None


def get_tts_manager() -> TTSManager:
    global _tts_manager
    if _tts_manager is None:
        _tts_manager = TTSManager()
    return _tts_manager


def speak_async(text: str):
    manager = get_tts_manager()
    manager.speak(text, block=False)


def speak_sync(text: str):
    manager = get_tts_manager()
    manager.speak(text, block=True)