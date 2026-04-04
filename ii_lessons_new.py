import re
import requests
import sqlite3
from datetime import datetime, date
import spacy
from spacy.matcher import Matcher
import random

API_KEY = "adf4cfb0273f49bee5663240951f9431"

try:
    nlp = spacy.load("ru_core_news_sm")
    print("Модель spaCy успешно загружена")
except OSError:
    print("Модель ru_core_news_sm не найдена. Устанавливаю...")
    import subprocess
    subprocess.run(["python", "-m", "spacy", "download", "ru_core_news_sm"])
    nlp = spacy.load("ru_core_news_sm")

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
    
    if "error" in data:
        return f"Ошибка API: {data['error'].get('info', 'Неизвестная ошибка')}"

    current = data["current"]
    temp = current.get("temperature")
    description_list = current.get("weather_descriptions", [])
    description = description_list[0] if description_list else "Нет данных"
    wind_speed = current.get("wind_speed")

    if temp is None:
        return "Не удалось получить температуру."

    return (f"Погода в городе {city}:\n"
            f"Температура: {temp}°C\n"
            f"Описание: {description}\n"
            f"Скорость ветра: {wind_speed} м/с")


def init_db():
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            chat_count INTEGER DEFAULT 0
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT,
            user_message TEXT,
            bot_response TEXT,
            intent TEXT,
            entities TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_name) REFERENCES users(name)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS weather_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT,
            city TEXT,
            request_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_name) REFERENCES users(name)
        )
    """)

    conn.commit()
    conn.close()
    
def save_or_update_user(name):
    try:
        conn = sqlite3.connect("bot.db")
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM users WHERE name = ?", (name,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            cursor.execute("""
                UPDATE users 
                SET last_seen = CURRENT_TIMESTAMP, 
                    chat_count = chat_count + 1 
                WHERE name = ?
            """, (name,))
            print(f"Обновлен пользователь: {name}")
        else:
            cursor.execute("""
                INSERT INTO users (name, chat_count) 
                VALUES (?, 1)
            """, (name,))
            print(f"Добавлен новый пользователь: {name}")
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Ошибка при сохранении пользователя: {e}")
        return False

def save_chat_message(user_name, user_message, bot_response, intent=None, entities=None):
    try:
        conn = sqlite3.connect("bot.db")
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO chat_history (user_name, user_message, bot_response, intent, entities)
            VALUES (?, ?, ?, ?, ?)
        """, (user_name, user_message, bot_response, intent, str(entities) if entities else None))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Ошибка при сохранении сообщения: {e}")
        return False

def save_weather_request(user_name, city):
    try:
        conn = sqlite3.connect("bot.db")
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO weather_requests (user_name, city)
            VALUES (?, ?)
        """, (user_name, city))
        
        conn.commit()
        print(f"Сохранен запрос погоды: {user_name}, {city}")
        conn.close()
        return True
    except Exception as e:
        print(f"Ошибка при сохранении запроса погоды: {e}")
        return False

def get_user_stats(user_name):
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT name, first_seen, last_seen, chat_count 
        FROM users 
        WHERE name = ?
    """, (user_name,))
    
    result = cursor.fetchone()
    conn.close()
    return result

def check_db():
    try:
        conn = sqlite3.connect("bot.db")
        cursor = conn.cursor()
        
        print("СОДЕРЖИМОЕ БАЗЫ ДАННЫХ")
        
        
        print("\n=== Таблица users ===")
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()
        if users:
            for user in users:
                print(f"ID: {user[0]}, Имя: {user[1]}, Первый визит: {user[2]}, Последний визит: {user[3]}, Сообщений: {user[4]}")
        else:
            print("Нет данных")
        
        print("\n=== Таблица weather_requests ===")
        cursor.execute("SELECT * FROM weather_requests")
        weather = cursor.fetchall()
        if weather:
            for req in weather:
                print(f"ID: {req[0]}, Пользователь: {req[1]}, Город: {req[2]}, Время: {req[3]}")
        else:
            print("Нет данных")
        
        print("\n=== Таблица chat_history ===")
        cursor.execute("SELECT * FROM chat_history")
        history = cursor.fetchall()
        if history:
            for msg in history:
                print(f"ID: {msg[0]}, Пользователь: {msg[1]}, Интент: {msg[4]}, Сущности: {msg[5]}")
                print(f"  Сообщение: {msg[2][:50]}...")
                print(f"  Ответ: {msg[3][:50]}...")
        else:
            print("Нет данных")
        
        print("="*50 + "\n")
        conn.close()
    except Exception as e:
        print(f"Ошибка при проверке БД: {e}")


class NLPProcessor:
    def __init__(self, nlp_model):
        self.nlp = nlp_model
        self.setup_matchers()
        
        self.intent_patterns = {
            'greeting': ['привет', 'здравствуй', 'добрый день', 'доброе утро', 'добрый вечер', 'хай', 'здарова', 'здравствуйте'],
            'farewell': ['пока', 'до свидания', 'всего доброго', 'до встречи', 'увидимся', 'прощай', 'до завтра'],
            'weather': ['погода', 'температура', 'градус', 'дождь', 'снег', 'ветер', 'холодно', 'тепло', 'прогноз', 'осадки'],
            'set_name': ['меня зовут', 'мое имя', 'называют', 'представься', 'познакомиться', 'зовут'],
            'time': ['время', 'час', 'минута', 'который час'],
            'date': ['дата', 'число', 'день недели', 'календарь', 'сегодня', 'какое сегодня'],
            'mood': ['дела', 'настроение', 'как ты', 'что делаешь', 'как жизнь'],
            'stats': ['статистика', 'сколько раз', 'активность', 'история', 'моя статистика'],
            'math': ['посчитай', 'сколько будет', 'плюс', 'минус', 'умножить', 'разделить', 'прибавить', 'отнять'],
            'help': ['помощь', 'помоги', 'что ты умеешь', 'команды', 'справка']
        }
        
    def setup_matchers(self):
        self.matcher = Matcher(self.nlp.vocab)
        
        city_pattern = [
            {'IS_TITLE': True, 'OP': '+'},
            {'IS_PUNCT': True, 'OP': '*'}
        ]
        self.matcher.add("CITY", [city_pattern])
        
        name_pattern = [
            {'LOWER': {'IN': ['меня', 'мое', 'моё']}},
            {'LOWER': {'IN': ['зовут', 'имя']}},
            {'IS_TITLE': True, 'OP': '+'}
        ]
        self.matcher.add("NAME", [name_pattern])
        
    def extract_cities(self, doc):
        cities = []
        
        matches = self.matcher(doc)
        for match_id, start, end in matches:
            if self.nlp.vocab.strings[match_id] == "CITY":
                span = doc[start:end]
                cities.append(span.text)
        
        for ent in doc.ents:
            if ent.label_ in ["GPE", "LOC"]:
                cities.append(ent.text)
        
        for i, token in enumerate(doc):
            if token.text.lower() in ['в', 'во', 'из', 'для', 'около'] and i + 1 < len(doc):
                next_token = doc[i + 1]
                if next_token.is_title and next_token.pos_ in ["PROPN", "NOUN"]:
                    cities.append(next_token.text)
        
        return list(set(cities))
    
    def extract_name(self, doc):
        names = []
        
        matches = self.matcher(doc)
        for match_id, start, end in matches:
            if self.nlp.vocab.strings[match_id] == "NAME":
                name_span = doc[start:end]
                for token in reversed(name_span):
                    if token.is_title and token.pos_ == "PROPN":
                        names.append(token.text)
                        break
        
        for ent in doc.ents:
            if ent.label_ == "PER":
                names.append(ent.text)
        
        if not names:
            for token in doc:
                if token.is_title and token.pos_ == "PROPN" and token.i > 0:
                    prev_token = doc[token.i - 1]
                    if prev_token.text.lower() in ['зовут', 'имя', 'это', '-', ':']:
                        names.append(token.text)
        
        return list(set(names))
    
    def extract_numbers(self, doc):
        numbers = []
        for token in doc:
            if token.like_num:
                try:
                    if '.' in token.text or ',' in token.text:
                        num = float(token.text.replace(',', '.'))
                    else:
                        num = float(token.text)
                    numbers.append(num)
                except ValueError:
                    pass
        return numbers
    
    def detect_intent(self, text):
        text_lower = text.lower().strip()
        
        for intent, keywords in self.intent_patterns.items():
            for keyword in keywords:
                if keyword in text_lower:
                    print(f"Найден интент '{intent}' по ключевому слову '{keyword}'")
                    return intent
        
        doc = self.nlp(text_lower)
        
        if text_lower.endswith('?') or any(token.text == '?' for token in doc):
            for token in doc:
                if token.lemma_ in ['погода', 'температура', 'градус']:
                    return 'weather'
                elif token.lemma_ in ['время', 'час']:
                    return 'time'
                elif token.lemma_ in ['дата', 'число']:
                    return 'date'
                elif token.lemma_ in ['имя', 'зовут']:
                    return 'set_name'
        
        math_words = ['плюс', 'минус', 'умножить', 'разделить', '+', '-', '*', '/', 'прибавить', 'отнять']
        if any(word in text_lower for word in math_words):
            return 'math'
        
        greeting_words = ['привет', 'здравствуй', 'добрый', 'хай']
        if any(word in text_lower for word in greeting_words) and len(text_lower.split()) < 4:
            return 'greeting'
        
        return 'unknown'
    
    def analyze(self, text):
        doc = self.nlp(text)
        
        analysis = {
            'text': text,
            'intent': self.detect_intent(text),
            'cities': self.extract_cities(doc),
            'names': self.extract_name(doc),
            'numbers': self.extract_numbers(doc),
            'tokens': [token.text for token in doc],
            'lemmas': [token.lemma_ for token in doc],
            'pos_tags': [token.pos_ for token in doc],
            'entities': [(ent.text, ent.label_) for ent in doc.ents],
            'is_question': text.strip().endswith('?')
        }
        
        print(f"NLP Анализ: {analysis}")
        return analysis


class ChatBot:
    def __init__(self):
        self.name = None
        self.nlp_processor = NLPProcessor(nlp)
        self.patterns = []
        self.register_patterns()
        init_db()
        print("Бот инициализирован с поддержкой NLP. База данных создана/проверена.")

    def register_patterns(self):
        self.patterns = [
            (re.compile(r"меня зовут ([а-яА-Яa-zA-Z\-]+)", re.IGNORECASE), self.set_name_regex),
            (re.compile(r"(\d+)\s*([\+\-\*\/])\s*(\d+)", re.IGNORECASE), self.math_operation),
        ]

    def set_name_regex(self, match):
        name = match.group(1).strip()
        self.name = name
        save_or_update_user(self.name)
        return f"Приятно познакомиться, {self.name}! Чем могу помочь?"

    def process_with_nlp(self, message):
        analysis = self.nlp_processor.analyze(message)
        intent = analysis['intent']
        cities = analysis['cities']
        names = analysis['names']
        numbers = analysis['numbers']
        
        print(f"Определен интент: {intent}")
        
        if intent == 'greeting':
            return self.greet_nlp()
        
        elif intent == 'farewell':
            return self.farewell_nlp()
        
        elif intent == 'weather':
            if cities:
                city = cities[0]
                if self.name:
                    save_weather_request(self.name, city)
                return get_weather(city)
            else:
                return "Для какого города вы хотите узнать погоду? Напишите, например: 'погода в Москве'"
        
        elif intent == 'set_name':
            if names:
                self.name = names[0]
                save_or_update_user(self.name)
                return f"Приятно познакомиться, {self.name}! Чем могу помочь?"
            else:
                return self.extract_name_from_text(message)
        
        elif intent == 'time':
            return self.get_time()
        
        elif intent == 'date':
            return self.get_date()
        
        elif intent == 'mood':
            return self.get_mood()
        
        elif intent == 'stats':
            return self.show_stats_nlp()
        
        elif intent == 'math':
            if numbers and len(numbers) >= 2:
                return self.process_math(message, numbers)
            else:
                return "Напишите пример, например: 'сколько будет 5 плюс 3'"
        
        elif intent == 'help':
            return self.get_help()
        
        return None

    def extract_name_from_text(self, message):
        name_patterns = [
            r"меня зовут ([а-яА-Яa-zA-Z\-]+)",
            r"мое имя ([а-яА-Яa-zA-Z\-]+)",
            r"я ([а-яА-Яa-zA-Z\-]+)",
            r"зовите меня ([а-яА-Яa-zA-Z\-]+)"
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                self.name = name
                save_or_update_user(self.name)
                return f"Приятно познакомиться, {self.name}!"
        
        return "Извините, я не понял ваше имя. Скажите 'меня зовут ...'"

    def greet_nlp(self):
        greetings = [
            f"Здравствуйте{', ' + self.name if self.name else ''}!",
            f"Привет{', ' + self.name if self.name else ''}! Рад вас видеть!",
            f"Добрый день{', ' + self.name if self.name else ''}! Чем могу помочь?",
            f"Здравствуйте{', ' + self.name if self.name else ''}! Как ваши дела?"
        ]
        return random.choice(greetings)

    def farewell_nlp(self):
        if self.name:
            save_or_update_user(self.name)
            farewells = [
                f"До свидания, {self.name}! Было приятно пообщаться.",
                f"Всего доброго, {self.name}! Заходите еще!",
                f"Пока, {self.name}! Хорошего дня!",
                f"До встречи, {self.name}! Буду ждать новых сообщений!"
            ]
        else:
            farewells = [
                "До свидания! Заходите еще!",
                "Всего доброго! Буду рад снова пообщаться!",
                "Пока! Хорошего дня!"
            ]
        return random.choice(farewells)

    def get_time(self):
        current_time = datetime.now().strftime("%H:%M")
        responses = [
            f"Сейчас {current_time}",
            f"Точное время: {current_time}",
            f"На часах {current_time}"
        ]
        return random.choice(responses)

    def get_date(self):
        today = date.today()
        responses = [
            f"Сегодня {today.strftime('%d.%m.%Y')}",
            f"На календаре {today.strftime('%d %B %Y')}",
            f"Сегодняшняя дата: {today.strftime('%d.%m.%Y')}"
        ]
        return random.choice(responses)

    def get_mood(self):
        moods = [
            "У меня всё отлично!",
            "Настроение прекрасное!",
            "Замечательно! Спасибо, что спросили!",
            "Всё хорошо, работаю, помогаю людям!"
        ]
        return random.choice(moods)

    def get_help(self):
        return ("Я понимаю естественный язык! Могу:\n"
                "Показать погоду (например: 'какая погода в Москве?')\n"
                "Запомнить ваше имя (например: 'меня зовут Александр')\n"
                "Показать статистику ('моя статистика')\n"
                "Посчитать ('сколько будет 5 плюс 3')\n"
                "Сказать время и дату\n"
                "Просто поболтать")

    def show_stats_nlp(self):
        if not self.name:
            return "Чтобы увидеть статистику, мне нужно знать ваше имя. Скажите 'меня зовут ...'"
        
        stats = get_user_stats(self.name)
        if stats:
            name, first_seen, last_seen, chat_count = stats
            try:
                first_seen_dt = datetime.strptime(first_seen, '%Y-%m-%d %H:%M:%S')
                last_seen_dt = datetime.strptime(last_seen, '%Y-%m-%d %H:%M:%S')
                first_seen = first_seen_dt.strftime('%d.%m.%Y %H:%M')
                last_seen = last_seen_dt.strftime('%d.%m.%Y %H:%M')
            except:
                pass
            
            return (f"Статистика для {name}:\n"
                   f"Первый визит: {first_seen}\n"
                   f"Последний визит: {last_seen}\n"
                   f"Сообщений: {chat_count}")
        return "Статистика не найдена"

    def math_operation(self, match):
        a = float(match.group(1))
        operator = match.group(2)
        b = float(match.group(3))
        
        if operator == '+':
            result = a + b
            operation = "плюс"
        elif operator == '-':
            result = a - b
            operation = "минус"
        elif operator == '*':
            result = a * b
            operation = "умножить на"
        elif operator == '/':
            if b != 0:
                result = a / b
                operation = "разделить на"
            else:
                return "Деление на ноль невозможно"
        else:
            return "Неизвестная операция"
        
        responses = [
            f"Результат: {result}",
            f"{a} {operation} {b} = {result}",
            f"Получается {result}"
        ]
        return random.choice(responses)

    def process_math(self, message, numbers):
        message_lower = message.lower()
        
        if len(numbers) >= 2:
            a, b = numbers[0], numbers[1]
            
            if 'плюс' in message_lower or '+' in message_lower or 'прибавить' in message_lower:
                return f"{a} + {b} = {a + b}"
            elif 'минус' in message_lower or '-' in message_lower or 'отнять' in message_lower:
                return f"{a} - {b} = {a - b}"
            elif 'умножить' in message_lower or '*' in message_lower:
                return f"{a} * {b} = {a * b}"
            elif 'разделить' in message_lower or '/' in message_lower:
                if b != 0:
                    return f"{a} / {b} = {a / b}"
                else:
                    return "Деление на ноль невозможно"
        
        return "Не могу распознать математическую операцию"

    def process(self, message):
        message = message.strip()
        
        if message.lower() in ['помощь', 'помоги', 'что ты умеешь']:
            return self.get_help()
        
        for pattern, handler in self.patterns:
            match = pattern.search(message)
            if match:
                response = handler(match)
                if self.name:
                    save_chat_message(self.name, message, response, 'regex_match', None)
                    save_or_update_user(self.name)
                return response
        
        response = self.process_with_nlp(message)
        
        if response is None:
            response = self.get_default_response()
        
        if self.name:
            analysis = self.nlp_processor.analyze(message)
            save_chat_message(self.name, message, response, 
                            analysis['intent'], 
                            {'cities': analysis['cities'], 
                             'names': analysis['names'],
                             'numbers': analysis['numbers']})
            save_or_update_user(self.name)
        
        return response

    def get_default_response(self):
        responses = [
            "Интересно... Расскажите подробнее.",
            "Я не совсем понял. Можете перефразировать?",
            "Хм, давайте поговорим о чем-то другом.",
            "Я учусь понимать людей. Что вы имели в виду?",
            "Извините, я еще не научился отвечать на такие вопросы.",
            "Можете задать вопрос по-другому?",
            "Напишите 'помощь', чтобы узнать, что я умею."
        ]
        return random.choice(responses)


def log_message(user, bot):
    with open("chat_log.txt", "a", encoding="utf-8") as f:
        f.write(f"{datetime.now()} USER: {user}\n")
        f.write(f"{datetime.now()} BOT: {bot}\n")
        f.write("-" * 50 + "\n")


def print_help():
    print("\n" + "="*50)
    print("СПРАВКА ПО КОМАНДАМ")
    
    print("Бот понимает естественный язык, поэтому можно спрашивать:")
    print("\nПОГОДА:")
    print("  • 'Какая погода в Москве?'")
    print("  • 'Сколько градусов в Питере?'")
    print("  • 'Будет дождь в Париже?'")
    print("  • 'Холодно сегодня в Лондоне?'")
    print("\nЗНАКОМСТВО:")
    print("  • 'Меня зовут Александр'")
    print("  • 'Моё имя Мария'")
    print("  • 'Я - Дмитрий'")
    print("\nСТАТИСТИКА:")
    print("  • 'Моя статистика'")
    print("  • 'Покажи мою активность'")
    print("  • 'Сколько раз я писал?'")
    print("\nМАТЕМАТИКА:")
    print("  • 'Сколько будет 5 + 3?'")
    print("  • '10 минус 4'")
    print("  • '7 умножить на 8'")
    print("\nВРЕМЯ И ДАТА:")
    print("  • 'Который час?'")
    print("  • 'Какое сегодня число?'")
    print("  • 'Какой сегодня день?'")
    print("\nОБЩЕНИЕ:")
    print("  • 'Привет', 'Здравствуйте'")
    print("  • 'Как дела?', 'Как настроение?'")
    print("  • 'Пока', 'До свидания'")
    print("\nКоманда 'выход' - завершение программы")
    print("Команда 'помощь' - показать эту справку")
    print("="*50 + "\n")


if __name__ == "__main__":
    print("Проверка установки spaCy модели...")
    print(f"Загруженные пайплайны spaCy: {nlp.pipe_names}")
    
    bot = ChatBot()
    
    print("Введите 'помощь' для получения справки по командам.")
    print("Введите 'выход' для завершения программы.\n")
    
    while True:
        try:
            user_input = input("Вы: ").strip()
            
            if user_input.lower() == 'выход':
                print("\nБот: До свидания! Заходите еще!")
                print("\n" + "="*50)
                print("ПРОВЕРКА БАЗЫ ДАННЫХ ПЕРЕД ВЫХОДОМ")
                check_db()
                break
            
            if user_input.lower() == 'помощь':
                print_help()
                continue
            
            if not user_input:
                continue
            
            response = bot.process(user_input)
            log_message(user_input, response)
            print(f"Бот: {response}")
            
        except KeyboardInterrupt:
            print("\n\nБот: До свидания! Программа завершена.")
            check_db()
            break
        except Exception as e:
            print(f"Произошла ошибка: {e}")
            print("Продолжаем работу...")


#import re
#import requests
#import sqlite3
#from datetime import datetime, date

#API_KEY = "adf4cfb0273f49bee5663240951f9431"

#def get_weather(self,city):
    #url = "https://api.weatherstack.com/current"
    #params = {
         #"access_key": API_KEY,
           #"query": city,
            #"units": "m",
            #"lang": "ru"
        #}
    #try:
        #response = requests.get(url, params=params, timeout=5)
    #except requests.exceptions.RequestException as e:
        #return f"Ошибка соединения: {e}"

    #if response.status_code != 200:
        #return "Не удалось получить данные о погоде."

    #data = response.json()

    #current = data["current"]
    #temp = current.get("temperature")
    #description_list = current.get("weather_descriptions", [])
    #description = description_list[0]
    #wind_speed = current.get("wind_speed")

    #if temp is None:
        #return "Не удалось получить температуру."

    #return f"Погода в городе {city}:\nТемпература: {temp}°C\nОписание: {description}\nСкорость ветра: {wind_speed} м/с"


#def init_db():
    #conn = sqlite3.connect("bot.db")
    #cursor = conn.cursor()

    #cursor.execute("""
        #CREATE TABLE IF NOT EXISTS users (
            #user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            #name TEXT UNIQUE,
            #first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            #last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            #chat_count INTEGER DEFAULT 0
        #)
    #""")
    
    #cursor.execute("""
        #CREATE TABLE IF NOT EXISTS chat_history (
            #id INTEGER PRIMARY KEY AUTOINCREMENT,
            #user_name TEXT,
            #user_message TEXT,
            #bot_response TEXT,
            #timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            #FOREIGN KEY (user_name) REFERENCES users(name)
        #)
    #""")
    
    #cursor.execute("""
        #CREATE TABLE IF NOT EXISTS weather_requests (
            #id INTEGER PRIMARY KEY AUTOINCREMENT,
            #user_name TEXT,
            #city TEXT,
            #request_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            #FOREIGN KEY (user_name) REFERENCES users(name)
        #)
    #""")

    #conn.commit()
    #conn.close()
    
#def save_or_update_user(name):
    #conn = sqlite3.connect("bot.db")
    #cursor = conn.cursor()
    
    #cursor.execute("SELECT name FROM users WHERE name = ?", (name,))
    #existing_user = cursor.fetchone()
    
    #if existing_user:
        #cursor.execute("""
            #UPDATE users 
            #SET last_seen = CURRENT_TIMESTAMP, 
                #chat_count = chat_count + 1 
            #WHERE name = ?
        #""", (name,))
    #else:
        #cursor.execute("""
            #INSERT INTO users (name, chat_count) 
            #VALUES (?, 1)
        #""", (name,))
    
    #conn.commit()
    #conn.close()

#def save_chat_message(user_name, user_message, bot_response):
    #conn = sqlite3.connect("bot.db")
    #cursor = conn.cursor()
    
    #cursor.execute("""
        #INSERT INTO chat_history (user_name, user_message, bot_response)
        #VALUES (?, ?, ?)
    #""", (user_name, user_message, bot_response))
    
    #conn.commit()
    #conn.close()

#def save_weather_request(user_name, city):
    #conn = sqlite3.connect("bot.db")
    #cursor = conn.cursor()
    
    #cursor.execute("""
        #INSERT INTO weather_requests (user_name, city)
        #VALUES (?, ?)
    #""", (user_name, city))
    
    #conn.commit()
    #conn.close()

#def get_user_stats(user_name):
    #conn = sqlite3.connect("bot.db")
    #cursor = conn.cursor()
    
    #cursor.execute("""
        #SELECT name, first_seen, last_seen, chat_count 
        #FROM users 
        #WHERE name = ?
    #""", (user_name,))
    
    #result = cursor.fetchone()
    #conn.close()
    #return result


#class ChatBot:
    #def __init__(self):
        #self.name = None
        #self.patterns = []
        #self.register_patterns()
        #init_db()

    #def register_patterns(self):
        #self.patterns = [
            #(re.compile(r"^(привет|здравствуйте|добрый день)$", re.IGNORECASE), self.greet),
            #(re.compile(r"^(пока|до свидания)$", re.IGNORECASE), self.farewell),
            #(re.compile(r"погода в ([а-яА-Яa-zA-Z\-]+)", re.IGNORECASE), self.weather),
            #(re.compile(r"как (у тебя )?дела", re.IGNORECASE), self.mood),
            #(re.compile(r"какое сегодня число", re.IGNORECASE), self.day),
            #(re.compile(r"меня зовут ([а-яА-Яa-zA-Z\-]+)", re.IGNORECASE), self.set_name),
            #(re.compile(r"(\d+)\s*\+\s*(\d+)", re.IGNORECASE), self.addition),
            #(re.compile(r"(\d+)\s*\-\s*(\d+)", re.IGNORECASE), self.subs),
            #(re.compile(r"(моя статистика|статистика)", re.IGNORECASE), self.show_stats)
        #]

    #def set_name(self, match):
        #self.name = match.group(1)
        #save_or_update_user(self.name)
        #return f"Приятно познакомиться, {self.name}!"

    #def greet(self, match):
        #if self.name:
            #return f"Здравствуйте, {self.name}!"
        #return "Здравствуйте!"

    #def farewell(self, match):
        #if self.name:
            #save_or_update_user(self.name)
        #return "До свидания!"

    #def weather(self, match):
        #city = match.group(1)
        #if self.name:
            #save_weather_request(self.name, city)
        #return get_weather(self, city)    

    #def mood(self, match):
        #return "Настроение прекрасно!"

    #def day(self, match):
        #td = date.today()
        #return f"Сегодняшняя дата: {td}"

    #def addition(self, match):
        #a = float(match.group(1))
        #b = float(match.group(2))
        #return f"Долно быть: {a + b}"
    
    #def subs(self, match):
        #a = float(match.group(1))
        #b = float(match.group(2))
        #return f"Долно быть: {a - b}"
    
    #def show_stats(self, match):
        #if not self.name:
            #return "Сначала представься"
        
        #stats = get_user_stats(self.name)
        #if stats:
            #name, first_seen, last_seen, chat_count = stats
            #return (f"Статистика для {name}:\n"
                   #f"Первый визит: {first_seen}\n"
                   #f"Последний визит: {last_seen}\n"
                   #f"Сообщений: {chat_count}")
        #return "Статистика не найдена"

    #def process(self, message):
        #message = message.strip()
        #for pattern, handler in self.patterns:
            #match = pattern.search(message)
            #if match:
                #response = handler(match)
                #if self.name:
                    #save_chat_message(self.name, message, response)
                    #save_or_update_user(self.name)
                #return response
        #response = "Ни слова не понял"
        #if self.name:
            #save_chat_message(self.name, message, response)
            #save_or_update_user(self.name)
        #return response

#def log_message(user, bot):
    #with open("chat_log.txt", "a", encoding="utf-8") as f:
        #f.write(f"{datetime.now()} USER: {user}\n")
        #f.write(f"{datetime.now()} BOT: {bot}\n")

#if __name__ == "__main__":
    #bot = ChatBot()
    #while True:
        #user_input = input("Вы: ")
        #response = bot.process(user_input)
        #log_message(user_input, response)
        #print("Бот:", response)