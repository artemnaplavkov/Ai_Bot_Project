import re
from datetime import datetime
import sqlite3
import datetime as dt
import requests
import spacy

DB_NAME = "chatbot.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            user_message TEXT NOT NULL,
            bot_response TEXT NOT NULL
        )
    """)
    cur.execute("PRAGMA table_info(logs)")
    columns = [col[1] for col in cur.fetchall()]
    if 'intent' not in columns:
        cur.execute("ALTER TABLE logs ADD COLUMN intent TEXT")
    if 'city' not in columns:
        cur.execute("ALTER TABLE logs ADD COLUMN city TEXT")
    conn.commit()
    conn.close()

def save_log(user_message: str, bot_response: str, intent: str = None, city: str = None):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    timestamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(
        "INSERT INTO logs (timestamp, user_message, bot_response, intent, city) VALUES (?, ?, ?, ?, ?)",
        (timestamp, user_message, bot_response, intent, city)
    )
    conn.commit()
    conn.close()

API_KEY = "adf4cfb0273f49bee5663240951f9431"
BASE_URL = "http://api.weatherstack.com/current"

def get_weather(city):
    if not city:
        return "Укажите название города."

    params = {
        "access_key": API_KEY,
        "query": city,
        "units": "m"
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            error_info = data["error"].get("info", "Неизвестная ошибка")
            return f"Ошибка API погоды: {error_info}"

        if "current" not in data or "location" not in data:
            return "Не удалось получить данные о погоде для указанного места."

        location_name = data["location"]["name"]
        country = data["location"]["country"]
        current = data["current"]

        temperature = current["temperature"]
        weather_descriptions = current["weather_descriptions"][0] if current["weather_descriptions"] else "нет данных"
        wind_speed = current["wind_speed"]

        return (f"Погода в {location_name}, {country}: {temperature}°C, "
                f"{weather_descriptions}, ветер {wind_speed} км/ч")

    except requests.exceptions.Timeout:
        return "Сервер погоды не ответил вовремя. Попробуйте позже."
    except requests.exceptions.ConnectionError:
        return "Ошибка подключения к серверу погоды. Проверьте интернет-соединение."
    except requests.exceptions.RequestException as e:
        return f"Ошибка при запросе погоды: {e}"
    except (KeyError, ValueError) as e:
        return f"Не удалось обработать данные о погоде. Ошибка: {e}"

class ChatBot:
    def __init__(self):
        self.nlp = spacy.load("ru_core_news_sm")
        self.patterns = []
        self._register_patterns()
        self.last_intent = None
        self.last_city = None
        init_db()

    def _register_patterns(self):
        self.patterns.append((re.compile(r"^(привет|здравствуйте)", re.IGNORECASE), self.greet))
        self.patterns.append((re.compile(r"^(пока|до свидания)", re.IGNORECASE), self.farewell))
        self.patterns.append((re.compile(r"^сумма\s+(\d+\.?\d*)\s+(\d+\.?\d*)", re.IGNORECASE), self.addition))
        self.patterns.append((re.compile(
            r"(сколько времени|который час|текущее время|дата и время|какой сегодня день|какая дата|какое сегодня число)",
            re.IGNORECASE), self.time))
        self.default_handler = self.unknown

    def _extract_city(self, text):
        doc = self.nlp(text)
        for ent in doc.ents:
            if ent.label_ in ("LOC", "GPE"):
                lemmas = [token.lemma_ for token in ent]
                return " ".join(lemmas).strip()
        return None

    def _is_weather_query(self, text):
        keywords = ["погода", "прогноз", "температура", "градус", "потепление", "похолодание"]
        return any(kw in text.lower() for kw in keywords)

    def _process_nlp(self, text):
        if self._is_weather_query(text):
            city = self._extract_city(text)
            if city:
                return get_weather(city), "weather", city
            else:
                return "Укажите город в вашем запросе.", "weather_unknown", None
        return None

    def greet(self, match): 
        return "Здравствуйте! Чем могу помочь?"
    
    def farewell(self, match): 
        return "До свидания!"
    
    def addition(self, match):
        try:
            a, b = float(match.group(1)), float(match.group(2))
            return f"Результат: {a + b}"
        except ValueError:
            return "Ошибка: введите два числа."
    
    def time(self, match):
        return datetime.now().strftime("Сейчас время %H:%M:%S, %d.%m.%Y")
    
    def unknown(self, match): 
        return "Извините, я не понимаю ваш запрос."

    def process(self, message: str) -> str:
        nlp_result = self._process_nlp(message)
        if nlp_result:
            response, intent, city = nlp_result
            self.last_intent, self.last_city = intent, city
            return response

        for pattern, handler in self.patterns:
            if match := pattern.search(message):
                response = handler(match)
                if handler == self.greet: 
                    self.last_intent = "greet"
                elif handler == self.farewell: 
                    self.last_intent = "farewell"
                elif handler == self.addition: 
                    self.last_intent = "addition"
                elif handler == self.time: 
                    self.last_intent = "time"
                else: 
                    self.last_intent = "unknown"
                self.last_city = None
                return response

        self.last_intent, self.last_city = "unknown", None
        return self.unknown(None)

def main():
    bot = ChatBot()
    print("Привет! Я бот. Я умею показывать погоду, складывать числа, отвечать на вопросы о времени.\n")

    while True:
        user_input = input("Вы: ").strip()
        if not user_input:
            continue

        response = bot.process(user_input)
        print("Бот:", response)

        save_log(user_input, response, bot.last_intent, bot.last_city)

        if response == "До свидания!":
            break

if __name__ == "__main__":
    main()