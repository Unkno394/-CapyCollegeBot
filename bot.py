import logging
import traceback
from difflib import SequenceMatcher
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from g4f.client import Client as G4FClient
from telegram import InputFile

# --- НАСТРОЙКИ ---
TOKEN = "7297351981:AAEsCvSquNsOfeQ6n86cJMhcY_p3aASzisE"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- СООБЩЕНИЯ И КЛАВИАТУРА ---

WELCOME_MESSAGE = """
Приветствую, студент РКСИ! 👋

Я твой помощник по колледжу. Отвечу на все часто задаваемые вопросы студентов.🔥

Просто задай мне вопрос, и я постараюсь помочь!🚀
"""
MAIN_MENU = ReplyKeyboardMarkup([
    ["🚌 Проездная карта", "🏥 Медпункт"],
    ["📚 Расписание", "🔑 Восстановление пропуска"],
    ["📄 Возврат изъятых документов", "📝 Объяснительная"],
    ["📝 Заявление", "📚 Библиотека"],
    ["❓ Помощь"]
], resize_keyboard=True)

BUTTON_TO_TOPIC = {
    "🚌 Проездная карта": "проездная карта",
    "🏥 Медпункт": "медпункт",
    "📚 Расписание": "расписание",
    "🔑 Восстановление пропуска": "восстановление пропуска",
    "📄 Возврат изъятых документов": "возврат изъятых документов",
    "📝 Объяснительная": "объяснительная",
    "📝 Заявление": "заявление",
    "📚 Библиотека": "библиотека",
    "❓ Помощь": "помощь"
}

FIXED_RESPONSES = {
    "медпункт": {
        "answer": "🏥 Кабинет 115.\n📍 Первый корпус.\n👩‍⚕️ Райф Татьяна Адольфовна.\n\n🏥 Кабинет 110.\n📍 Второй корпус\n👩‍⚕️ Игнатьева Наталья Георгиевна.",
        "keywords": ["медпункт", "медкабинет", "врач", "райф", "татьяна", "аптечка", "медицинский", "больница", "доктор"]
    },
    "расписание": {
        "answer": "📅 Расписание:\n• @turtle_rksi_bot\n• @RKSIplanshetkabot",
        "keywords": ["расписание", "пары", "график", "занятия", "учебный план"]
    },
    "проездная карта": {
        "answer": "📌 Где оформить проездную карту?\n📍 Карту можно оформить на улице Халтуринский 28.\n\n📝 Что нужно взять с собой?\n• Паспорт 📄\n• Справка, подтверждающая обучение в колледже 🎓\n(Оформляется в 1 корпусе, каб. 120 — Отдел кадров.\nЗаведующая: Ирина Викторовна)\n• 90 рублей 💰\n\nС этой картой все поездки станут в 2 раза дешевле! 👐 Если вдруг карта потеряется – не переживайте! 😊 Её можно легко восстановить, и все ваши средства перейдут на новую карточку",
        "keywords": ["проездная", "проездной", "карта", "транспортная", "метро", "автобус"]
    },
    "восстановление пропуска": {
        "answer": "🔐 Шаги:\n1. Написать заявление — каб. 118а\n2. Оплатить 300₽ (скачать квитанцию: <a href='https://rksi.ru/doc/college/cartlost.pdf'>тут</a>)\n3. Чек — в 118а\n4. Получить карту через 1-3 дня\n\n⚠ Временно выдают бумажный пропуск.",
        "keywords": ["пропуск", "восстановить", "потерял", "новая карта", "электронный", "сломалась"]
    },
    "возврат изъятых документов": {
        "answer": "🔴 <b>Причины изъятия:</b>\n▸ Отсутствие сменной обуви 👞🚫\n▸ Нет пропуска 🆔❌\n\n🟢<b> Как вернуть документы?</b>\n1. Если документ изъят за отсутствие сменки:\n▸ Напишите объяснительную и сдайте её в каб. 219\n2. Если изъяли за отсутствие пропускного:\n▸ Оформите новый пропускной и посетите кабинет 118а\n\n⚡ Лайфхак:\nВсегда носите сменку и не теряйте пропуск — это сэкономит ваше время! ⏳",
        "keywords": ["документы", "изъяли", "вернуть", "пропуск", "забрали"]
    },
    "объяснительная": {
        "answer": "📝 <b>Как оформить объяснительную:</b>\n1. Укажите ФИО, группу и дату.\n2. Опишите причину.\n3. Подпись и дата составления.",
        "keywords": ["объяснительная", "опоздание", "пропуск", "оформить объяснительную"],
        "photo": "static/photo1.jpg"  
    },
    "заявление": {
        "answer": "📝 <b>Как оформить заявление:</b>\n1. Укажите ФИО, группу и дату.\n2. Опишите суть заявления кратко и ясно.\n3. Подпишите и поставьте дату.",
        "keywords": ["заявление", "написать заявление", "оформить заявление", "пример заявления"],
        "photo": "static/photo2.jpg"  
    },
    "библиотека":{
        "answer": "📚Ауд. 215, 1 корпус\n👩‍💼 Заведующая:\nЕкатерина Ивановна Кривошеева\n🕒Время работы библиотеки:\nпонедельник — суббота, 8:30 — 17:00.",
        "keywords": []
    },
    "помощь": {
        "answer": "📌 Просто задай вопрос или выбери нужный пункт из меню 👇",
        "keywords": []
    }
}

class QuestionAnalyzer:
    def __init__(self):
        try:
            self.client = G4FClient()
            self.neuro_enabled = True
        except Exception as e:
            logger.warning(f"Нейросеть недоступна: {e}")
            self.neuro_enabled = False

    def similar(self, a: str, b: str) -> float:
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    def find_best_match(self, text: str, keywords: list) -> tuple:
        text = text.lower()
        best_match = None
        highest_score = 0

        for keyword in keywords:
            if keyword in text:
                return keyword, 1.0
            for word in text.split():
                score = self.similar(word, keyword)
                if score > 0.6 and score > highest_score:
                    highest_score = score
                    best_match = keyword
        return best_match, highest_score

    async def analyze_with_neuro(self, text: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Определи тему: 1-Медпункт, 2-Расписание, 3-Проездная карта, 4-Восстановление пропуска, 5-Другое. Ответь цифрой."},
                    {"role": "user", "content": text}
                ],
                timeout=10
            )
            result = response.choices[0].message.content.strip()
            return {
                "1": "медпункт",
                "2": "расписание",
                "3": "проездная карта",
                "4": "восстановление пропуска"
            }.get(result, "помощь")
        except Exception as e:
            logger.error(f"Ошибка нейросети: {e}")
            return None

    async def detect_topic(self, text: str) -> str:
        if text in BUTTON_TO_TOPIC:
            return BUTTON_TO_TOPIC[text]

        for topic, data in FIXED_RESPONSES.items():
            _, score = self.find_best_match(text, data["keywords"])
            if score > 0.6:
                return topic

        if self.neuro_enabled:
            neuro_topic = await self.analyze_with_neuro(text)
            if neuro_topic:
                return neuro_topic

        return "помощь"

# --- ОБРАБОТЧИКИ ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME_MESSAGE, reply_markup=MAIN_MENU)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    logger.info(f"Вопрос: {user_text}")

    try:
        analyzer = QuestionAnalyzer()
        topic = await analyzer.detect_topic(user_text)
        logger.info(f"Тема определена: {topic}")

        if topic in FIXED_RESPONSES:
            data = FIXED_RESPONSES[topic]

            # Если есть изображение
            if "photo" in data:
                with open(data["photo"], "rb") as photo_file:
                    await update.message.reply_photo(
                        photo=InputFile(photo_file),
                        caption=data["answer"],
                        parse_mode="HTML",
                        reply_markup=MAIN_MENU
                    )
            else:
                await update.message.reply_text(
                    data["answer"],
                    parse_mode="HTML",
                    reply_markup=MAIN_MENU
                )
        else:
            await update.message.reply_text(
                "Не совсем понял ваш вопрос. Попробуйте переформулировать или выберите из меню 👇",
                reply_markup=MAIN_MENU
            )
    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {e}")
        traceback.print_exc()
        await update.message.reply_text(
            "Произошла ошибка при обработке запроса. Попробуйте позже.",
            reply_markup=MAIN_MENU
        )

# --- ЗАПУСК БОТА ---

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Бот запущен ✅")
    app.run_polling()

if __name__ == "__main__":
    main()