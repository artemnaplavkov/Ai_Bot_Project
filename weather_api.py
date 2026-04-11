import requests

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

def should_take_umbrella(city):
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
            return f"Ошибка: {data['error'].get('info', 'Неизвестная ошибка')}"
        
        if "current" not in data:
            return "Не удалось получить данные о погоде."
        
        weather_desc = data["current"]["weather_descriptions"]
        rain_keywords = ["дождь", "ливень", "гроза", "морось", "осадки"]
        
        has_rain = any(keyword in desc.lower() for desc in weather_desc for keyword in rain_keywords)
        
        if has_rain:
            return f"Да, в {city} сейчас или ожидается дождь. Лучше взять зонт!"
        else:
            return f"Нет, в {city} дождя не ожидается. Зонт не понадобится."
            
    except Exception as e:
        return f"Ошибка при проверке погоды: {e}"