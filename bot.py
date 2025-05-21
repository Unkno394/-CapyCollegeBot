import logging
import traceback
from difflib import SequenceMatcher
from telegram import Update, ReplyKeyboardMarkup, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from g4f.client import Client as G4FClient
import asyncio
import os

# --- НАСТРОЙКИ ---
TOKEN = "7297351981:AAEsCvSquNsOfeQ6n86cJMhcY_p3aASzisE"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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
        "keywords": ["медпункт", "медкабинет", "врач", "райф", "татьяна", "аптечка", "медицинский", "больница", "доктор"],
        "photo": None
    },
    "расписание": {
        "answer": "📅 Расписание:\n• @turtle_rksi_bot\n• @RKSIplanshetkabot",
        "keywords": ["расписание", "пары", "график", "занятия", "учебный план"],
        "photo": None
    },
    "проездная карта": {
        "answer": "📌 Где оформить проездную карту?\n📍 Карту можно оформить на улице Халтуринский 28.\n\n📝 Что нужно взять с собой?\n• Паспорт 📄\n• Справка, подтверждающая обучение в колледже 🎓\n(Оформляется в 1 корпусе, каб. 120 — Отдел кадров.\nЗаведующая: Ирина Викторовна)\n• 90 рублей 💰\n\nС этой картой все поездки станут в 2 раза дешевле! 👐 Если вдруг карта потеряется – не переживайте! 😊 Её можно легко восстановить, и все ваши средства перейдут на новую карточку",
        "keywords": ["проездная", "проездной", "карта", "транспортная", "метро", "автобус"],
        "photo": None
    },
    "восстановление пропуска": {
        "answer": "🔐 Шаги:\n1. Написать заявление — каб. 118а\n2. Оплатить 300₽ (скачать квитанцию: <a href='https://rksi.ru/doc/college/cartlost.pdf'>тут</a>)\n3. Чек — в 118а\n4. Получить карту через 1-3 дня\n\n⚠ Временно выдают бумажный пропуск.",
        "keywords": ["пропуск", "восстановить", "потерял", "новая карта", "электронный", "сломалась"],
        "photo": None
    },
    "возврат изъятых документов": {
        "answer": "🔴 <b>Причины изъятия:</b>\n▸ Отсутствие сменной обуви 👞🚫\n▸ Нет пропуска 🆔❌\n\n🟢<b> Как вернуть документы?</b>\n1. Если документ изъят за отсутствие сменки:\n▸ Напишите объяснительную и сдайте её в каб. 219\n2. Если изъяли за отсутствие пропускного:\n▸ Оформите новый пропускной и посетите кабинет 118а\n\n⚡ Лайфхак:\nВсегда носите сменку и не теряйте пропуск — это сэкономит ваше время! ⏳",
        "keywords": ["документы", "изъяли", "вернуть", "пропуск", "забрали"],
        "photo": None
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
    "библиотека": {
        "answer": "📚Ауд. 215, 1 корпус\n👩‍💼 Заведующая:\nЕкатерина Ивановна Кривошеева\n🕒Время работы библиотеки:\nпонедельник — суббота, 8:30 — 17:00.",
        "keywords": [],
        "photo": None
    },
    "помощь": {
        "answer": "📌 Просто задай вопрос или выбери нужный пункт из меню 👇",
        "keywords": [],
        "photo": None
    }
}

class QuestionAnalyzer:
    def __init__(self):
        self.neuro_enabled = False
        try:
            self.client = G4FClient()
            self.neuro_enabled = True
        except Exception as e:
            logger.warning(f"Нейросеть недоступна: {e}")
        self.cache = {}

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
        if not self.neuro_enabled:
            return None
            
        try:
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Отвечай только одним словом: медпункт, расписание, проездная, пропуск, помощь"},
                        {"role": "user", "content": f"К какой теме относится: '{text}'?"}
                    ],
                    max_tokens=10
                ),
                timeout=5
            )
            result = response.choices[0].message.content.strip().lower()
            return result if result in FIXED_RESPONSES else "помощь"
        except Exception as e:
            logger.error(f"Ошибка нейросети: {e}")
            return None

    async def detect_topic(self, text: str) -> str:
        if text in self.cache:
            return self.cache[text]
            
        # Проверка точных совпадений с кнопками
        if text in BUTTON_TO_TOPIC:
            self.cache[text] = BUTTON_TO_TOPIC[text]
            return BUTTON_TO_TOPIC[text]

        # Поиск по ключевым словам
        for topic, data in FIXED_RESPONSES.items():
            _, score = self.find_best_match(text, data["keywords"])
            if score > 0.7:
                self.cache[text] = topic
                return topic

        # Обращение к нейросети только для длинных запросов
        if self.neuro_enabled and len(text.split()) > 2:
            neuro_topic = await self.analyze_with_neuro(text)
            if neuro_topic:
                self.cache[text] = neuro_topic
                return neuro_topic

        self.cache[text] = "помощь"
        return "помощь"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME_MESSAGE, reply_markup=MAIN_MENU)

async def send_response(update: Update, answer: str, photo_path: str = None):
    if photo_path and os.path.exists(photo_path):
        try:
            with open(photo_path, "rb") as photo_file:
                await update.message.reply_photo(
                    photo=InputFile(photo_file),
                    caption=answer,
                    parse_mode="HTML",
                    reply_markup=MAIN_MENU
                )
            return
        except Exception as e:
            logger.error(f"Ошибка отправки фото: {e}")
    
    await update.message.reply_text(
        answer,
        parse_mode="HTML",
        reply_markup=MAIN_MENU
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    logger.info(f"Вопрос: {user_text}")

    try:
        async with asyncio.timeout(8):
            analyzer = QuestionAnalyzer()
            topic = await analyzer.detect_topic(user_text)
            logger.info(f"Тема определена: {topic}")

            if topic in FIXED_RESPONSES:
                data = FIXED_RESPONSES[topic]
                await send_response(update, data["answer"], data.get("photo"))
            else:
                await send_response(update, "Не совсем понял ваш вопрос. Попробуйте переформулировать или выберите из меню 👇")
                
    except asyncio.TimeoutError:
        await send_response(update, "Время обработки запроса истекло. Попробуйте позже или задайте более конкретный вопрос.")
    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {e}")
        traceback.print_exc()
        await send_response(update, "Произошла ошибка при обработке запроса. Попробуйте позже.")

def main():
    # Создаем папку static если её нет
    if not os.path.exists("static"):
        os.makedirs("static")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()