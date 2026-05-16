from tts_manager import TTSManager, speak_async
import time


def test():
    print("Тестирование TTS Manager...")
    
    tts = TTSManager()
    
    phrases = [
        "Привет мир! Это тест голосового синтеза.",
        "Сегодня отличная погода на улице.",
        "Сейчас ровно три часа дня.",
        "Температура воздуха плюс двадцать градусов цельсия.",
        "Не забудьте взять зонт, возможен дождь."
    ]
    
    for phrase in phrases:
        print(f"Озвучивание: {phrase}")
        speak_async(phrase)
        time.sleep(2)
    
    print("Ожидание завершения воспроизведения...")
    tts.wait_for_completion()
    tts.shutdown()
    print("Тест завершён!")


if __name__ == "__main__":
    test()