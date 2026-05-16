from faster_whisper import WhisperModel
import sounddevice as sd
from scipy.io.wavfile import write
import re
import pyttsx3
import threading


class VoiceHandler:
    def __init__(self, model_name="base"):
        print("Загрузка модели Faster Whisper...")
        self.model = WhisperModel(model_name, device="cpu", compute_type="int8")
        self.tts_engine = None
        self._init_tts()
        print("Модель загружена")
    
    def _init_tts(self):
        try:
            self.tts_engine = pyttsx3.init()
            self.tts_engine.setProperty('rate', 150)
            self.tts_engine.setProperty('volume', 0.9)
            voices = self.tts_engine.getProperty('voices')
            for voice in voices:
                if 'russian' in voice.name.lower() or 'russian' in voice.id.lower():
                    self.tts_engine.setProperty('voice', voice.id)
                    break
            print("TTS движок инициализирован")
        except Exception as e:
            print(f"TTS не доступен: {e}")
            self.tts_engine = None
    
    def record_audio(self, filename="input.wav", seconds=5, fs=16000):
        print("Говорите...")
        audio = sd.rec(int(seconds * fs), samplerate=fs, channels=1, dtype='int16')
        sd.wait()
        write(filename, fs, audio)
        print("Запись завершена")
    
    def speech_to_text(self, filename="input.wav"):
        segments, info = self.model.transcribe(filename, language="ru")
        text = " ".join([segment.text for segment in segments])
        return text
    
    def clean_text(self, text):
        text = text.lower()
        text = re.sub(r'[^\w\s\u0400-\u052F]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def listen(self):
        self.record_audio()
        text = self.speech_to_text()
        cleaned = self.clean_text(text)
        print(f"Распознано: {cleaned}")
        return cleaned
    
    def speak(self, text):
        if self.tts_engine:
            print(f"Озвучивание: {text}")
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
        else:
            print(f"Текст: {text}")
    
    def speak_async(self, text):
        if self.tts_engine:
            thread = threading.Thread(target=self.speak, args=(text,))
            thread.daemon = True
            thread.start()
        else:
            print(f"Текст: {text}")


voice = VoiceHandler()


def listen():
    return voice.listen()


def speak(text):
    voice.speak(text)


def speak_async(text):
    voice.speak_async(text)