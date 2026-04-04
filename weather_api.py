import requests

# Вставьте сюда ваш действующий ключ доступа к API weatherstack
# Получить можно после бесплатной регистрации на https://weatherstack.com/
API_KEY = "YOUR_API_KEY"  # Замените на реальный ключ
BASE_URL = "http://api.weatherstack.com/current"

def get_weather(city):
    """
    Запрашивает текущую погоду для города через API weatherstack.com.
    Возвращает строку с температурой, описанием погоды и скоростью ветра.
    В случае ошибки возвращает сообщение о проблеме.
    """
    if not city:
        return "Укажите название города."

    params = {
        "access_key": API_KEY,
        "query": city,
        "units": "m"  # 'm' для метрической системы (температура в °C, скорость ветра в км/ч)
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
