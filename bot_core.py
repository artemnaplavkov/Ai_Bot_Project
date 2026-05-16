import re
import json
import random
import torch
import spacy
from datetime import datetime
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from weather_api import get_weather, should_take_umbrella
from database import init_db, save_log
from tts_manager import speak_async

from skills import WeatherSkill, TimeSkill, DateSkill, SmallTalkSkill, HelpSkill

class DialogState:
    START = "start"
    WAIT_CITY = "wait_city"

class ChatBot:
    def __init__(self, use_bert=True):
        try:
            self.nlp = spacy.load("ru_core_news_sm")
        except:
            print("Ошибка загрузки spaCy модели")
            self.nlp = None
        
        self.skills = {}
        self._register_skills()
        
        self.use_bert = use_bert
        self.bert_model = None
        self.bert_tokenizer = None
        self.label2id = None
        self.id2label = None
        
        if use_bert:
            self._load_bert_model()
        
        self.user_name = None
        self.user_states = {}
        self.last_intent = None
        self.last_confidence = None
        self.last_city = None
        
        init_db()
        self._print_skills_info()
    
    def _register_skills(self):
        skills_list = [
            WeatherSkill(),
            TimeSkill(),
            DateSkill(),
            SmallTalkSkill(),
            HelpSkill()
        ]
        
        for skill in skills_list:
            self.skills[skill.get_intent()] = skill
    
    def _print_skills_info(self):
        print("\n" + "="*50)
        print("Бот запущен!")
        print("="*50)
        print("Загруженные навыки:")
        for intent, skill in self.skills.items():
            print(f"   - {intent:12} -> {skill.name}")
        print("="*50 + "\n")
    
    def _load_bert_model(self):
        try:
            self.bert_tokenizer = AutoTokenizer.from_pretrained("intent_model_extended")
            self.bert_model = AutoModelForSequenceClassification.from_pretrained("intent_model_extended")
            self.bert_model.eval()
            
            with open("intent_model_extended/label2id.json", "r", encoding="utf-8") as f:
                self.label2id = json.load(f)
            self.id2label = {v: k for k, v in self.label2id.items()}
            print(f"BERT модель загружена. Распознает {len(self.label2id)} интентов")
            print(f"Доступные интенты: {list(self.id2label.values())}\n")
        except Exception as e:
            print(f"Ошибка загрузки BERT: {e}")
            print("Буду использовать regex для определения интентов\n")
            self.use_bert = False
    
    def _get_intent(self, message):
        if self.use_bert and self.bert_model:
            intent, confidence = self._get_intent_bert(message)
            intent = self._normalize_intent(intent)
            return intent, confidence
        else:
            return self._get_intent_regex(message), 0.7
    
    def _normalize_intent(self, intent):
        intent_map = {
            "greet": "greeting",
            "farewell": "farewell",
            "weather": "weather",
            "time": "time",
            "date": "date",
            "help": "help",
            "smalltalk": "smalltalk",
            "addition": "addition",
            "thanks": "thanks",
            "joke": "joke",
            "set_name": "set_name",
            "umbrella": "umbrella",
            "bot_name": "bot_name",
            "greeting": "greeting",
            "unknown": "unknown"
        }
        return intent_map.get(intent, "unknown")
    
    def _get_intent_bert(self, message):
        inputs = self.bert_tokenizer(
            message, 
            return_tensors="pt", 
            truncation=True, 
            max_length=128, 
            padding=True
        )
        
        with torch.no_grad():
            outputs = self.bert_model(**inputs)
            probs = torch.softmax(outputs.logits, dim=1)
            confidence, pred = torch.max(probs, dim=1)
        
        intent = self.id2label[pred.item()]
        return intent, confidence.item()
    
    def _get_intent_regex(self, message):
        text_lower = message.lower()
        
        if re.search(r"(погода|температура|прогноз|градус)", text_lower):
            return "weather"
        elif re.search(r"(сколько времени|который час|текущее время|время сейчас)", text_lower):
            return "time"
        elif re.search(r"(какое сегодня число|какая дата|сегодняшнее число|какой день)", text_lower):
            return "date"
        elif re.search(r"(привет|здравствуйте|добрый день|хай|салют|здорово)", text_lower):
            return "greeting"
        elif re.search(r"(пока|до свидания|увидимся|прощай|бывай|чао)", text_lower):
            return "farewell"
        elif re.search(r"(помощь|что ты умеешь|какие команды|расскажи о себе)", text_lower):
            return "help"
        elif re.search(r"(как дела|как настроение|как жизнь|что нового|как поживаешь)", text_lower):
            return "smalltalk"
        elif re.search(r"(\d+\s*\+\s*\d+)", text_lower):
            return "addition"
        elif re.search(r"(сумма\s+\d+\s+\d+)", text_lower):
            return "addition"
        elif re.search(r"(спасибо|благодарю|мерси)", text_lower):
            return "thanks"
        elif re.search(r"(шутку|анекдот|рассмеши|пошути)", text_lower):
            return "joke"
        elif re.search(r"(меня зовут|моё имя|зови меня|называй меня)", text_lower):
            return "set_name"
        elif re.search(r"(зонт|дождь|брать зонт|нужен ли зонт)", text_lower):
            return "umbrella"
        elif re.search(r"(как тебя зовут|кто ты|твоё имя|как тебя называть)", text_lower):
            return "bot_name"
        else:
            return "unknown"
    
    def _extract_city(self, text):
        if self.nlp:
            doc = self.nlp(text)
            for ent in doc.ents:
                if ent.label_ in ("LOC", "GPE"):
                    return ent.text
        
        cities = ["москва", "спб", "питер", "казань", "новосибирск", 
                  "екатеринбург", "сочи", "воронеж", "ростов"]
        for city in cities:
            if city in text.lower():
                return city
        return None
    
    def _get_state(self, user_id):
        return self.user_states.get(user_id, DialogState.START)
    
    def _set_state(self, user_id, state):
        self.user_states[user_id] = state
    
    def process(self, message: str, user_id: str = "default") -> str:
        state = self._get_state(user_id)
        
        if state == DialogState.WAIT_CITY:
            city = message.strip()
            if city:
                response = get_weather(city)
                self.last_city = city
                self._set_state(user_id, DialogState.START)
                self._print_debug(message, "weather", 0.9, response)
                return response
            return "Пожалуйста, укажите город."
        
        intent, confidence = self._get_intent(message)
        self.last_intent = intent
        self.last_confidence = confidence
        
        context = {
            'user_name': self.user_name,
            'city': self._extract_city(message) if intent == "weather" else None
        }
        
        if intent in self.skills:
            response = self.skills[intent].execute(message, context)
            
            if intent == "weather" and "В каком городе" in response:
                self._set_state(user_id, DialogState.WAIT_CITY)
            
            self._print_debug(message, intent, confidence, response)
            return response
        
        response = self._handle_other_intents(intent, message)
        self._print_debug(message, intent, confidence, response)
        return response
    
    def process_with_voice(self, message: str, user_id: str = "default", voice_enabled: bool = True) -> str:
        response = self.process(message, user_id)
        
        if voice_enabled and response:
            speak_async(response)
        
        return response
    
    def _handle_other_intents(self, intent, message):
        if intent == "greeting":
            if self.user_name:
                return f"Здравствуйте, {self.user_name}! Чем могу помочь?"
            return "Здравствуйте! Чем могу помочь?"
        
        elif intent == "farewell":
            return "До свидания! Хорошего дня!"
        
        elif intent == "addition":
            match = re.search(r"(\d+\.?\d*)\s*\+\s*(\d+\.?\d*)", message)
            if match:
                try:
                    a, b = float(match.group(1)), float(match.group(2))
                    return f"Результат: {a} + {b} = {a + b}"
                except:
                    return "Ошибка при сложении"
            match2 = re.search(r"сумма\s+(\d+\.?\d*)\s+(\d+\.?\d*)", message)
            if match2:
                try:
                    a, b = float(match2.group(1)), float(match2.group(2))
                    return f"Результат: {a} + {b} = {a + b}"
                except:
                    return "Ошибка при сложении"
            return "Не понял выражение. Например: 2+2 или сумма 5 и 3"
        
        elif intent == "thanks":
            thanks = ["Пожалуйста!", "Всегда рад помочь!", "Обращайтесь!", "Не за что!"]
            return random.choice(thanks)
        
        elif intent == "joke":
            jokes = [
                "Почему программисты путают Хэллоуин и Рождество? Потому что 31 Oct = 25 Dec!",
                "Сколько программистов нужно, чтобы заменить лампочку? Ни одного, это аппаратная проблема.",
                "Есть 10 типов людей: те, кто понимает двоичную систему, и те, кто не понимает.",
                "Что сказал ноль восьмёрке? Хороший поясок!"
            ]
            return random.choice(jokes)
        
        elif intent == "set_name":
            match = re.search(r"(?:меня зовут|моё имя|называй меня|зови меня|я)\s+([а-яА-Яa-zA-Z\-]+)", message, re.IGNORECASE)
            if match:
                self.user_name = match.group(1)
                return f"Приятно познакомиться, {self.user_name}!"
            return "Не понял имя. Скажите 'меня зовут ...'"
        
        elif intent == "umbrella":
            city = self._extract_city(message)
            if city:
                self.last_city = city
                return should_take_umbrella(city)
            return "В каком городе узнать про зонт? Например: 'нужен ли зонт в Москве'"
        
        elif intent == "bot_name":
            return "Меня зовут Бот-Помощник! Я создан, чтобы отвечать на вопросы о погоде, времени и не только."
        
        else:
            return "Извините, я не понимаю. Скажите 'помощь' чтобы узнать, что я умею."
    
    def _print_debug(self, message, intent, confidence, response):
        print(f"\n[DEBUG] Пользователь: {message}")
        print(f"[DEBUG] Интент: {intent}")
        print(f"[DEBUG] Уверенность: {confidence:.4f}")
        if intent in self.skills:
            print(f"[DEBUG] Навык: {self.skills[intent].name}")
        print(f"[DEBUG] Ответ: {response}\n")