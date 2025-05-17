from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from g4f.client import Client as G4FClient
import logging
import re
from difflib import SequenceMatcher

TOKEN = "7297351981:AAEsCvSquNsOfeQ6n86cJMhcY_p3aASzisE"

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Фиксированные ответы
FIXED_RESPONSES = {
    "медпункт": {
        "answer": "Кабинет 115. Заведующая — Райф Татьяна Адольфовна (первый корпус).\nКабинет 110. Заведующая медпунктом — Игнатьева Наталья Георгиевна (второй корпус).",
        "keywords": ["медпункт", "медкабинет", "врач", "райф", "татьяна", "аптечка", "медицинский", "больница", "доктор"]
    },
    "расписание": {
        "answer": "Расписание: @turtle_rksi_bot или @RKSIplanshetkabot",
        "keywords": ["расписание", "пары", "график", "занятия", "когда учимся", "учебный план"]
    }
}

DEFAULT_ANSWER = "Уточните вопрос у куратора или на сайте колледжа."
WELCOME_MESSAGE = """
Приветствую, студент РКСИ! 👋

Я твой помощник по колледжу. Могу подсказать:
• Где находится медпункт 🏥
• Где посмотреть расписание 📅
• И многое другое

Просто задай мне вопрос, и я постараюсь помочь!

P.S. Не забывай, что колледж - это святое, а пары лучше не пропускать 😉
"""

class QuestionAnalyzer:
    def __init__(self):
        try:
            self.client = G4FClient()
            self.neuro_enabled = True
        except:
            logger.warning("Нейросеть недоступна! Будем использовать улучшенный текстовый анализ")
            self.neuro_enabled = False
    
    def similar(self, a: str, b: str) -> float:
        """Вычисляет схожесть строк (0-1)"""
        return SequenceMatcher(None, a, b).ratio()
    
    def find_best_match(self, text: str, keywords: list) -> tuple:
        """Находит наиболее подходящее ключевое слово"""
        text = text.lower()
        best_match = None
        highest_score = 0
        
        for keyword in keywords:
            # Ищем точные вхождения
            if keyword in text:
                return keyword, 1.0
            
            # Ищем похожие слова
            words = text.split()
            for word in words:
                score = self.similar(word, keyword)
                if score > 0.7 and score > highest_score:  # Порог схожести
                    highest_score = score
                    best_match = keyword
        
        return best_match, highest_score
    
    async def detect_topic(self, text: str) -> str:
        """Определяет тему вопроса с учетом опечаток"""
        # Сначала проверяем через улучшенный текстовый анализ
        for topic, data in FIXED_RESPONSES.items():
            match, score = self.find_best_match(text, data["keywords"])
            if score > 0.75:  # Достаточно высокая схожесть
                logger.info(f"Найдено совпадение: {topic} (схожесть: {score:.2f})")
                return topic
        
        # Если не нашли и нейросеть доступна - пробуем через нее
        if self.neuro_enabled:
            try:
                response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{
                        "role": "system",
                        "content": "Определи тему вопроса:\n"
                                  "1. Медпункт\n2. Расписание\n3. Другое\n"
                                  "Ответь только цифрой."
                    }, {
                        "role": "user", 
                        "content": f"Вопрос: '{text}'\nОтвет:"
                    }],
                    timeout=10
                )
                result = response.choices[0].message.content.strip()
                
                return {
                    "1": "медпункт",
                    "2": "расписание"
                }.get(result, "другое")
            except Exception as e:
                logger.error(f"Ошибка нейросети: {str(e)}")
        
        return "другое"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await update.message.reply_text(WELCOME_MESSAGE)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    logger.info(f"Получен вопрос: {user_text}")
    
    analyzer = QuestionAnalyzer()
    topic = await analyzer.detect_topic(user_text)
    logger.info(f"Определена тема: {topic}")
    
    if topic in FIXED_RESPONSES:
        await update.message.reply_text(FIXED_RESPONSES[topic]["answer"])
    else:
        await update.message.reply_text(DEFAULT_ANSWER)

def main():
    app = Application.builder().token(TOKEN).build()
    
    # Добавляем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    app.run_polling()

if __name__ == "__main__":
    print("Бот запущен...")
    main()

    






    