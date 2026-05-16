from bot_core import ChatBot
from database import save_log
from tts_manager import get_tts_manager, speak_async
import uuid
import signal
import sys
import time


def signal_handler(sig, frame):
    print("\n\nЗавершение работы...")
    tts_manager = get_tts_manager()
    tts_manager.shutdown()
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, signal_handler)
    
    bot = ChatBot(use_bert=True)
    user_id = str(uuid.uuid4())[:8]
    
    print("\nИнициализация голосового движка Coqui TTS...")
    tts_manager = get_tts_manager()
    print(f"TTS готов. Кэш содержит {tts_manager.get_cache_size()} файлов")
    
    print("\nБот запущен с использованием BERT модели + голосовым выводом")
    print("Все ответы бота будут озвучиваться автоматически")
    print("Команды: 'выход' - завершить, 'очистить кэш' - удалить аудиофайлы")
    print("-" * 50)
    
    welcome = "Здравствуйте! Я голосовой помощник. Чем могу помочь?"
    print(f"Бот: {welcome}")
    speak_async(welcome)
    
    while True:
        user_input = input("\nВы: ").strip()
        
        if not user_input:
            continue
        
        if user_input.lower() in ['выход', 'exit', 'quit']:
            farewell = "До свидания! Хорошего дня!"
            print(f"Бот: {farewell}")
            speak_async(farewell)
            time.sleep(1)
            save_log(user_input, farewell, "farewell", None, user_id)
            break
        
        elif user_input.lower() in ['очистить кэш', 'clear cache']:
            tts_manager.clear_cache()
            msg = "Кэш аудиофайлов очищен"
            print(f"Бот: {msg}")
            speak_async(msg)
            continue
        
        elif user_input.lower() in ['статус кэша', 'cache status']:
            size = tts_manager.get_cache_size()
            msg = f"В кэше {size} аудиофайлов"
            print(f"Бот: {msg}")
            speak_async(msg)
            continue
        
        response = bot.process_with_voice(user_input, user_id, voice_enabled=True)
        print(f"Бот: {response}")
        
        save_log(user_input, response, bot.last_intent, bot.last_city, user_id)
    
    tts_manager.shutdown()


if __name__ == "__main__":
    main()