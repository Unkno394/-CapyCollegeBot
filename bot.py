from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from g4f.client import Client as G4FClient
import logging
from difflib import SequenceMatcher

TOKEN = "7297351981:AAEsCvSquNsOfeQ6n86cJMhcY_p3aASzisE"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FIXED_RESPONSES = {
    "медпункт": {
        "answer": "🏥 Кабинет 115.\n📍 Первый корпус.\n👩‍⚕️ Заведующая — Райф Татьяна Адольфовна.\n\n🏥 Кабинет 110.\n📍 Второй корпус\n👩‍⚕️ Заведующая медпунктом — Игнатьева Наталья Георгиевна.",
        "keywords": ["медпункт", "медкабинет", "врач", "райф", "татьяна", "аптечка", "медицинский", "больница", "доктор"]
    },
    "расписание": {
        "answer": "📅 Расписание:\n• @turtle_rksi_bot\n• @RKSIplanshetkabot",
        "keywords": ["расписание", "пары", "график", "занятия", "когда учимся", "учебный план"]
    },
    "проездная карта": {
        "answer": "📌 Где оформить проездную карту?\n📍 Карту можно оформить на улице Халтуринский 28.\n\n📝 Что нужно взять с собой?\n• Паспорт 📄\n• Справка, подтверждающая обучение в колледже 🎓\n(Оформляется в 1 корпусе, каб. 120 — Отдел кадров.\nЗаведующая: Ирина Викторовна)\n• 90 рублей 💰\n\nС этой картой все поездки станут в 2 раза дешевле! 👐 Если вдруг карта потеряется – не переживайте! 😊 Её можно легко восстановить, и все ваши средства перейдут на новую карточку.",
        "keywords": ["проездная", "проездной", "карта", "транспортная", "оформить проездной", "метро", "автобус", "где оформить карту"]
    }
}

MAIN_MENU = ReplyKeyboardMarkup([
    ["🚌 Проездная карта", "🏥 Медпункт"],
    ["📚 Расписание","❓ Помощь"]
], resize_keyboard=True)

WELCOME_MESSAGE = """
Приветствую, студент РКСИ! 👋

Я твой помощник по колледжу. Могу подсказать:
• Где находится медпункт 🏥
• Где посмотреть расписание 📅
• Где оформить проездную карту 🚌
• И многое другое

Просто задай мне вопрос, и я постараюсь помочь!

P.S. Не забывай, что колледж - это святое, а пары лучше не пропускать 😉
"""

class QuestionAnalyzer:
    def __init__(self):
        try:
            self.client = G4FClient()
            self.neuro_enabled = True
            logger.info("Нейросеть успешно инициализирована")
        except Exception as e:
            logger.warning(f"Нейросеть недоступна! Ошибка: {str(e)}. Будем использовать улучшенный текстовый анализ")
            self.neuro_enabled = False
    
    def similar(self, a: str, b: str) -> float:
        """Вычисляет схожесть строк (0-1) с учетом опечаток"""
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()
    
    def find_best_match(self, text: str, keywords: list) -> tuple:
        """Находит наиболее подходящее ключевое слово"""
        text = text.lower()
        best_match = None
        highest_score = 0
        
        for keyword in keywords:
            if keyword in text:
                return keyword, 1.0
            words = text.split()
            for word in words:
                score = self.similar(word, keyword)
                if score > 0.6 and score > highest_score:
                    highest_score = score
                    best_match = keyword
        
        return best_match, highest_score
    
    async def analyze_with_neuro(self, text: str) -> str:
        """Анализ вопроса с помощью нейросети"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{
                    "role": "system",
                    "content": "Определи тему вопроса:\n"
                              "1. Медпункт\n2. Расписание\n3. Проездная карта\n4. Другое\n"
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
                "2": "расписание",
                "3": "проездная карта"
            }.get(result, "помощь")
        except Exception as e:
            logger.error(f"Ошибка нейросети: {str(e)}")
            return None
    
    async def detect_topic(self, text: str) -> str:
        """Определяет тему вопроса с учетом опечаток"""
        text_lower = text.lower()

        for topic, data in FIXED_RESPONSES.items():
            match, score = self.find_best_match(text, data["keywords"])
            if score > 0.6:  
                logger.info(f"Найдено совпадение: {topic} (схожесть: {score:.2f})")
                return topic
        if self.neuro_enabled:
            neuro_topic = await self.analyze_with_neuro(text)
            if neuro_topic:
                return neuro_topic
        
        return "помощь"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await update.message.reply_text(
        WELCOME_MESSAGE,
        reply_markup=MAIN_MENU
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    logger.info(f"Получен вопрос: {user_text}")
    
    try:
        analyzer = QuestionAnalyzer()
        topic = await analyzer.detect_topic(user_text)
        logger.info(f"Определена тема: {topic}")
        
        if topic in FIXED_RESPONSES:
            await update.message.reply_text(
                FIXED_RESPONSES[topic]["answer"],
                reply_markup=MAIN_MENU
            )
        else:
            await update.message.reply_text(
                "Не совсем понял ваш вопрос. Попробуйте переформулировать или выберите пункт из меню ниже.",
                reply_markup=MAIN_MENU
            )
    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {str(e)}")
        await update.message.reply_text(
            "Произошла ошибка при обработке вашего запроса. Попробуйте позже.",
            reply_markup=MAIN_MENU
        )

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Бот запускается...")
    app.run_polling()

if __name__ == "__main__":
    main()
    