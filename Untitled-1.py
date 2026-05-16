import os
import re
from datetime import datetime, date
import requests
import sqlite3
import spacy
import numpy as np
import json
import hashlib
import threading
import unicodedata
import soundfile as sf
import pygame
from num2words import num2words
from voice import listen

user_id = 1
user_states = {}

WEATHER_TRANSLATIONS = {
    "Sunny": "Солнечно",
    "Clear": "Ясно",
    "Partly cloudy": "Переменная облачность",
    "Cloudy": "Облачно",
    "Overcast": "Пасмурно",
    "Light rain": "Небольшой дождь",
    "Moderate rain": "Умеренный дождь",
    "Heavy rain": "Сильный дождь",
    "Rain": "Дождь",
    "Thunderstorm": "Гроза",
    "Snow": "Снег",
    "Light snow": "Небольшой снег",
    "Fog": "Туман",
    "Mist": "Дымка",
    "Haze": "Мгла",
}

pygame.mixer.init()

import torch
device = torch.device('cpu')
model, _ = torch.hub.load('snakers4/silero-models', 'silero_tts', language='ru', speaker='v3_1_ru')
model.to(device)

nlp = spacy.load("ru_core_news_md")

API_KEY = "adf4cfb0273f49bee5663240951f9431"

cache = {}
os.makedirs("tts_cache", exist_ok=True)


def get_cache_path(text):
    text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
    return f"tts_cache/{text_hash}.wav"

def speak(text):
    path = get_cache_path(text)
    if text not in cache:
        if os.path.exists(path):
            cache[text] = path
        else:
            audio = model.apply_tts(text=text, speaker='eugene', sample_rate=48000)
            sf.write(path, audio, 48000)
            cache[text] = path

    pygame.mixer.music.load(cache[text])
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.wait(100)

def speak_async(text):
    threading.Thread(target=speak, args=(text,)).start()

def normalize_date_ru(date_str):
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        day = dt.day
        month = dt.month
        year = dt.year
        
        months_gen = {
            1: "января", 2: "февраля", 3: "марта", 4: "апреля",
            5: "мая", 6: "июня", 7: "июля", 8: "августа",
            9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
        }
        
        day_word = num2words(day, lang='ru') + " " + months_gen[month]
        year_word = num2words(year, lang='ru')
        return f"{day_word} {year_word} года"
    except:
        return date_str

def normalize_text_for_tts(text):
    date_pattern = re.compile(r'\b(\d{4})-(\d{2})-(\d{2})\b')
    text = date_pattern.sub(lambda m: normalize_date_ru(m.group(0)), text)
    
    text = re.sub(r'\s+', ' ', text).strip()
    text = unicodedata.normalize('NFC', text)
    text = text.replace("°C", " градусов Цельсия")
    text = text.replace("°", " градусов")
    text = text.replace("м/с", " метров в секунду")
    text = text.replace("N/A", "нет данных")
    
    def replace_number(match):
        num_str = match.group(0)
        try:
            num = int(num_str)
        except ValueError:
            return num_str
        if -2000 <= num <= 2000:
            return num2words(num, lang='ru')
        else:
            return num_str
    
    text = re.sub(r'\b\d+\b', replace_number, text)
    
    return text

class DialogState:
    START = "start"
    WAIT_CITY = "wait_city"


def init_db():
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            user_input TEXT,
            bot_response TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_user(user_id, name):
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO users (user_id, name) VALUES (?, ?)",
        (user_id, name)
    )
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def log_to_db(user_input, bot_response):
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()
    timestamp = datetime.now().isoformat()
    cursor.execute(
        "INSERT INTO logs (timestamp, user_input, bot_response) VALUES (?, ?, ?)",
        (timestamp, user_input, bot_response)
    )
    conn.commit()
    conn.close()

def log_message(user, bot):
    with open("chat_log.txt", "a", encoding="utf-8") as f:
        f.write(f"{datetime.now()} USER: {user}\n")
        f.write(f"{datetime.now()} BOT: {bot}\n")

def set_state(user_id, state):
    user_states[user_id] = state

def get_state(user_id):
    return user_states.get(user_id, DialogState.START)

def get_weather(city):
    url = "https://api.weatherstack.com/current"
    params = {
        "access_key": API_KEY,
        "query": city,
        "units": "m",
        "lang": "ru"
    }
    try:
        response = requests.get(url, params=params, timeout=5)
    except requests.exceptions.RequestException as e:
        return f"Ошибка соединения: {e}"

    if response.status_code != 200:
        return "Не удалось получить данные о погоде."

    data = response.json()
    if "current" not in data:
        return "Не удалось найти город или получить погоду."

    current = data["current"]
    temp = current.get("temperature", "N/A")
    description_list = current.get("weather_descriptions", [])
    if description_list:
        eng_description = description_list[0]
        ru_description = WEATHER_TRANSLATIONS.get(eng_description, eng_description)
    else:
        ru_description = "нет данных"
    wind_speed = current.get("wind_speed", "N/A")

    return f"Погода в городе {city}:\n Температура: {temp}°C.\n Описание: {ru_description}.\n Скорость ветра: {wind_speed} м/с."

def extract_city(text):
    doc = nlp(text)
    for ent in doc.ents:
        if ent.label_ in ["GPE", "LOC"]:
            return ent.lemma_
    return "NotFound"


class ChatBot:
    def __init__(self):
        self.name = get_user(user_id)
        self.exit_flag = False
        self.register_patterns()

    def register_patterns(self):
        self.patterns = [
            (re.compile(r"^(привет|здравствуйте|добрый день|хай|салют|здорово)$", re.IGNORECASE), self.greet),
            (re.compile(r"^(пока|до свидания|увидимся|прощай|бывай|выход)$", re.IGNORECASE), self.farewell),
            (re.compile(r"погода в ([а-яА-Яa-zA-Z\-]+)", re.IGNORECASE), self.weather),
            (re.compile(r"как (у тебя )?дела|как настроение|как жизнь", re.IGNORECASE), self.mood),
            (re.compile(r"какое сегодня число|какая дата|сегодняшнее число", re.IGNORECASE), self.day),
            (re.compile(r"меня зовут ([а-яА-Яa-zA-Z\-]+)", re.IGNORECASE), self.set_name),
            (re.compile(r"(\d+)\s*\+\s*(\d+)", re.IGNORECASE), self.addition),
            (re.compile(r"(\d+)\s*\-\s*(\d+)", re.IGNORECASE), self.subs),
            (re.compile(r"сколько времени|который час|текущее время", re.IGNORECASE), self.handle_time),
            (re.compile(r"помощь|что ты умеешь|какие команды", re.IGNORECASE), self.handle_help),
            (re.compile(r"спасибо|благодарю|мерси", re.IGNORECASE), self.handle_thx),
            (re.compile(r"расскажи шутку|анекдот|рассмеши|пошути", re.IGNORECASE), self.handle_joke),
        ]

    def set_name(self, match=None, name=None):
        if match:
            name = match.group(1)
        self.name = name
        save_user(user_id, name)
        return f"Приятно познакомиться, {self.name}!"

    def greet(self, match=None):
        if self.name:
            return f"Здравствуйте, {self.name}!"
        return "Здравствуйте! Чем могу помочь?"

    def farewell(self, match=None):
        self.exit_flag = True
        return "До свидания! Хорошего дня!"

    def weather(self, match=None):
        if match:
            raw_city = match.group(1)
            city_doc = nlp(raw_city)
            city = city_doc[0].lemma_ if city_doc else raw_city
            return get_weather(city)
        return "В каком городе узнать погоду?"

    def mood(self, match=None):
        return "У меня всё отлично! Как ваши дела?"

    def day(self, match=None):
        td = date.today()
        return f"Сегодня {td.strftime('%d.%m.%Y')}"

    def addition(self, match=None):
        if match:
            a = float(match.group(1))
            b = float(match.group(2))
            return f"Результат: {a} + {b} = {a + b}"
        return "Не понял выражение."

    def subs(self, match=None):
        if match:
            a = float(match.group(1))
            b = float(match.group(2))
            return f"Результат: {a} - {b} = {a - b}"
        return "Не понял выражение."

    def handle_greet(self, message):
        return self.greet()

    def handle_farewell(self, message):
        return self.farewell()
    
    def handle_time(self, message=None):
        now = datetime.now()
        return f"Сейчас {now.strftime('%H:%M:%S')}"

    def handle_weather(self, message):
        city = extract_city(message)
        if city != "NotFound":
            return get_weather(city)
        else:
            set_state(user_id, DialogState.WAIT_CITY)
            return "В каком городе вас интересует погода?"

    def handle_mood(self, message):
        return self.mood()

    def handle_day(self, message):
        return self.day()

    def handle_set_name(self, message):
        match = re.search(r"(?:меня зовут|моё имя|называй меня|зови меня|я)\s+([а-яА-Яa-zA-Z\-]+)", message, re.IGNORECASE)
        if match:
            name = match.group(1)
            return self.set_name(name=name)
        return "Не понял, как вас зовут."

    def handle_addition(self, message):
        match = re.search(r"(\d+)\s*\+\s*(\d+)", message)
        if match:
            return self.addition(match)
        return "Не смог распознать выражение."
    
    def handle_help(self, message):
        return "Я умею:\n- Здороваться и прощаться\n- Рассказывать погоду\n- Показывать время\n- Называть дату\n- Запоминать ваше имя\n- Складывать и вычитать числа\n- Рассказывать шутки\n- Отвечать голосом"
    
    def handle_thx(self, message):
        return "Всегда пожалуйста! Рад помочь!"
    
    def handle_joke(self, message):
        import random
        jokes = [
            "Почему программисты путают Хэллоуин и Рождество? Потому что 31 Oct = 25 Dec!",
            "Сколько программистов нужно, чтобы заменить лампочку? Ни одного, это аппаратная проблема.",
            "Есть 10 типов людей: те, кто понимает двоичную систему, и те, кто не понимает.",
            "Что сказал ноль восьмёрке? Хороший поясок!"
        ]
        return random.choice(jokes)

    def handle_subs(self, message):
        match = re.search(r"(\d+)\s*-\s*(\d+)", message)
        if match:
            return self.subs(match)
        return "Не смог распознать выражение."

    def handle_unknown(self, message):
        return "Извините, я не понимаю. Скажите 'помощь' чтобы узнать, что я умею."

    def process(self, message):
        return self.fallback_regex(message)

    def fallback_regex(self, message):
        for pattern, handler in self.patterns:
            match = pattern.search(message.lower())
            if match:
                return handler(match)
        return "Извините, я не понимаю. Скажите 'помощь' чтобы узнать, что я умею."

def handle_message(user_id, text):
    state = get_state(user_id)
    if state == DialogState.WAIT_CITY:
        city = extract_city(text)
        set_state(user_id, DialogState.START)
        return get_weather(city)
    else:
        return bot.process(text)

if __name__ == "__main__":
    init_db()
    bot = ChatBot()
    print("Бот запущен! Зажмите Ctrl и говорите в микрофон...")

    while True:
        user_input = listen()
        if not user_input:
            continue

        response = handle_message(user_id, user_input)

        log_message(user_input, response)
        log_to_db(user_input, response)
        print("Бот:", response)

        if response:
            clean_text = normalize_text_for_tts(response)
            speak_async(clean_text)
        if bot.exit_flag:
            break