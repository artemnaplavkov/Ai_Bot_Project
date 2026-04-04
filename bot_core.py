import re
from datetime import datetime
import spacy
from weather_api import get_weather
from database import init_db

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

    def greet(self, match): return "Здравствуйте! Чем могу помочь?"
    def farewell(self, match): return "До свидания!"
    def addition(self, match):
        try:
            a, b = float(match.group(1)), float(match.group(2))
            return f"Результат: {a + b}"
        except ValueError:
            return "Ошибка: введите два числа."
    def time(self, match):
        return datetime.now().strftime("Сейчас время %H:%M:%S, %d.%m.%Y")
    def unknown(self, match): return "Извините, я не понимаю ваш запрос."


    def process(self, message: str) -> str:
        nlp_result = self._process_nlp(message)
        if nlp_result:
            response, intent, city = nlp_result
            self.last_intent, self.last_city = intent, city
            return response

        for pattern, handler in self.patterns:
            if match := pattern.search(message):
                response = handler(match)
                if handler == self.greet: self.last_intent = "greet"
                elif handler == self.farewell: self.last_intent = "farewell"
                elif handler == self.addition: self.last_intent = "addition"
                elif handler == self.time: self.last_intent = "time"
                else: self.last_intent = "unknown"
                self.last_city = None
                return response

        self.last_intent, self.last_city = "unknown", None
        return self.unknown(None)