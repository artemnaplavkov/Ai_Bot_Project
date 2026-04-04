from bot_core import ChatBot
from database import save_log

def main():
    bot = ChatBot()
    user_id = "default" 
    print("Привет! Я бот. Я умею показывать погоду (с запросом города и даты), складывать числа, отвечать на вопросы о времени.\n")

    while True:
        user_input = input("Вы: ").strip()
        if not user_input:
            continue

        response = bot.process(user_id, user_input)
        print("Бот:", response)
        save_log(user_input, response, bot.last_intent, bot.last_city)

        if response == "До свидания!":
            break

if __name__ == "__main__":
    main()