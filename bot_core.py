import re
from datetime import datetime
import random
import spacy
from weather_api import get_weather, should_take_umbrella
from database import init_db

class DialogState:
    START = "start"
    WAIT_CITY = "wait_city"

class ChatBot:
    def __init__(self):
        try:
            self.nlp = spacy.load("ru_core_news_sm")
        except:
            print("Ошибка загрузки spaCy модели. Установите: python -m spacy download ru_core_news_sm")
            self.nlp = None
        self.user_name = None
        self.user_states = {}
        self.user_data = {}
        self.last_intent = None
        self.last_confidence = None
        self.last_city = None
        init_db()

    def _get_state(self, user_id):
        return self.user_states.get(user_id, DialogState.START)

    def _set_state(self, user_id, state):
        self.user_states[user_id] = state

    def _get_user_data(self, user_id):
        if user_id not in self.user_data:
            self.user_data[user_id] = {}
        return self.user_data[user_id]

    def _extract_city(self, text):
        if self.nlp:
            doc = self.nlp(text)
            for ent in doc.ents:
                if ent.label_ in ("LOC", "GPE"):
                    return ent.text
        common_cities = ["москва", "спб", "питер", "казань", "новосибирск", "екатеринбург", "сочи", "воронеж", "ростов"]
        for city in common_cities:
            if city in text.lower():
                return city
        return None

    def _get_intent(self, message):
        text_lower = message.lower()
        
        if re.search(r"(привет|здравствуйте|добрый день|доброе утро|здрасте|хай|салют)", text_lower):
            return "greeting", 0.95
        elif re.search(r"(пока|до свидания|всего хорошего|прощай|увидимся|бай)", text_lower):
            return "farewell", 0.95
        elif re.search(r"(погода|температура|прогноз|градус)", text_lower):
            return "weather", 0.9
        elif re.search(r"(\d+\s*\+\s*\d+)", text_lower):
            return "addition", 0.9
        elif re.search(r"(сумма\s+\d+\s+\d+)", text_lower):
            return "addition", 0.9
        elif re.search(r"(сколько времени|который час|текущее время|дата|какое сегодня число)", text_lower):
            return "time", 0.95
        elif re.search(r"(как дела|как настроение|что делаешь|как ты|как жизнь)", text_lower):
            return "mood", 0.9
        elif re.search(r"(меня зовут|моё имя|называй меня|зови меня|я\s+[а-яА-Я]+)", text_lower):
            return "set_name", 0.9
        elif re.search(r"(помощь|что ты умеешь|какие команды)", text_lower):
            return "help", 0.95
        elif re.search(r"(спасибо|благодарю|мерси)", text_lower):
            return "thanks", 0.95
        elif re.search(r"(отлично|хорошо|прекрасно|классно|супер)", text_lower):
            return "positive", 0.85
        elif re.search(r"(плохо|ужасно|не очень|грустно)", text_lower):
            return "negative", 0.85
        elif re.search(r"(шутку|рассмеши|анекдот|смешное)", text_lower):
            return "joke", 0.9
        elif re.search(r"(как тебя зовут|кто ты|твоё имя)", text_lower):
            return "bot_name", 0.95
        elif re.search(r"(зонт|дождь|осадки|брать зонт|нужен ли зонт)", text_lower):
            return "umbrella", 0.9
        else:
            return "unknown", 0.5

    def greet(self):
        if self.user_name:
            return f"Здравствуйте, {self.user_name}! Чем могу помочь?"
        return "Здравствуйте! Чем могу помочь?"

    def farewell(self):
        return "До свидания!"

    def addition(self, message):
        match = re.search(r"(\d+\.?\d*)\s*\+\s*(\d+\.?\d*)", message)
        if match:
            try:
                a, b = float(match.group(1)), float(match.group(2))
                return f"Результат: {a + b}"
            except:
                return "Ошибка: введите два числа"
        match2 = re.search(r"сумма\s+(\d+\.?\d*)\s+(\d+\.?\d*)", message)
        if match2:
            try:
                a, b = float(match2.group(1)), float(match2.group(2))
                return f"Результат: {a + b}"
            except:
                return "Ошибка: введите два числа"
        return "Не понял выражение. Например: 2+2 или сумма 5 и 3"

    def time(self):
        return datetime.now().strftime("Сейчас время %H:%M:%S, %d.%m.%Y")

    def handle_mood(self):
        moods = ["У меня всё отлично! Спасибо, что спросили!", 
                 "Настроение прекрасное! А у вас?", 
                 "Я в хорошем настроении, помогаю людям!"]
        return random.choice(moods)

    def handle_set_name(self, message):
        match = re.search(r"(?:меня зовут|моё имя|называй меня|зови меня|я)\s+([а-яА-Яa-zA-Z\-]+)", message, re.IGNORECASE)
        if match:
            self.user_name = match.group(1)
            return f"Приятно познакомиться, {self.user_name}!"
        return "Не понял, как вас зовут. Скажите 'меня зовут ...'"

    def handle_help(self):
        return "Я умею:\n- Показывать погоду ('погода в Москве')\n- Складывать числа ('2+2')\n- Сказать время ('сколько времени')\n- Отвечать на 'как дела'\n- Запоминать ваше имя ('меня зовут ...')\n- Сказать, нужен ли зонт ('стоит ли брать зонт в Москве')\n- Рассказывать шутки"

    def handle_thanks(self):
        thanks = ["Пожалуйста!", "Всегда рад помочь!", "Обращайтесь!", "Не за что!"]
        return random.choice(thanks)

    def handle_positive(self):
        positives = ["Отлично! Рад это слышать!", "Прекрасно!", "Здорово!"]
        return random.choice(positives)

    def handle_negative(self):
        negatives = ["Сочувствую. Может, погода поднимет настроение?", 
                     "Всё наладится! Рассказать шутку?", 
                     "Печально слышать. Чем могу помочь?"]
        return random.choice(negatives)

    def handle_joke(self):
        jokes = [
            "Почему программисты путают Хэллоуин и Рождество? Потому что 31 Oct = 25 Dec!",
            "Сколько программистов нужно, чтобы заменить лампочку? Ни одного, это аппаратная проблема.",
            "Есть 10 типов людей: те, кто понимает двоичную систему, и те, кто не понимает.",
            "Что сказал ноль восьмёрке? Хороший поясок!"
        ]
        return random.choice(jokes)

    def handle_bot_name(self):
        return "Меня зовут Бот-Помощник! Я создан, чтобы отвечать на вопросы о погоде, времени и не только."

    def handle_umbrella(self, message):
        city = self._extract_city(message)
        if city:
            response = should_take_umbrella(city)
            self.last_city = city
            return response
        else:
            return "Для ответа на вопрос про зонт, скажите, в каком городе? Например: 'стоит ли брать зонт в Москве'"

    def unknown(self):
        return "Извините, я не понимаю. Скажите 'помощь' чтобы узнать, что я умею."

    def process(self, message: str) -> str:
        user_id = "default"
        state = self._get_state(user_id)
        
        self.last_intent = None
        self.last_confidence = None
        self.last_city = None

        if state == DialogState.WAIT_CITY:
            city = message.strip()
            if city:
                response = get_weather(city)
                self.last_intent = "weather"
                self.last_confidence = 0.8
                self.last_city = city
                self._set_state(user_id, DialogState.START)
                self._print_debug(message, response)
                return response
            else:
                return "Пожалуйста, укажите город."

        intent, confidence = self._get_intent(message)
        self.last_intent = intent
        self.last_confidence = confidence

        if intent == "weather":
            city = self._extract_city(message)
            if city:
                response = get_weather(city)
                self.last_city = city
                self._print_debug(message, response)
                return response
            else:
                self._set_state(user_id, DialogState.WAIT_CITY)
                response = "В каком городе вас интересует погода?"
                self._print_debug(message, response)
                return response
        
        elif intent == "greeting":
            response = self.greet()
            self._print_debug(message, response)
            return response
        
        elif intent == "farewell":
            response = self.farewell()
            self._print_debug(message, response)
            return response
        
        elif intent == "addition":
            response = self.addition(message)
            self._print_debug(message, response)
            return response
        
        elif intent == "time":
            response = self.time()
            self._print_debug(message, response)
            return response
        
        elif intent == "mood":
            response = self.handle_mood()
            self._print_debug(message, response)
            return response
        
        elif intent == "set_name":
            response = self.handle_set_name(message)
            self._print_debug(message, response)
            return response
        
        elif intent == "help":
            response = self.handle_help()
            self._print_debug(message, response)
            return response
        
        elif intent == "thanks":
            response = self.handle_thanks()
            self._print_debug(message, response)
            return response
        
        elif intent == "positive":
            response = self.handle_positive()
            self._print_debug(message, response)
            return response
        
        elif intent == "negative":
            response = self.handle_negative()
            self._print_debug(message, response)
            return response
        
        elif intent == "joke":
            response = self.handle_joke()
            self._print_debug(message, response)
            return response
        
        elif intent == "bot_name":
            response = self.handle_bot_name()
            self._print_debug(message, response)
            return response
        
        elif intent == "umbrella":
            response = self.handle_umbrella(message)
            self._print_debug(message, response)
            return response
        
        else:
            response = self.unknown()
            self._print_debug(message, response)
            return response

    def _print_debug(self, user_message, bot_response):
        print(f"\n[DEBUG] Пользователь: {user_message}")
        print(f"[DEBUG] Определённый интент: {self.last_intent}")
        print(f"[DEBUG] Уверенность: {self.last_confidence:.4f}")
        print(f"[DEBUG] Город: {self.last_city}")
        print(f"[DEBUG] Ответ бота: {bot_response}\n")