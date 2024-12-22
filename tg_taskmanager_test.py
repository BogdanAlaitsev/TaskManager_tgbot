import asyncio
from aiogram import Bot, Dispatcher, Router, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timedelta
import logging
from db_taskmanager import init_db, add_task, load_user_tasks, delete_task

# Установим уровень логирования для отображения важной информации
logging.basicConfig(level=logging.INFO)

# Токен API бота
API_TOKEN = "7065691771:AAFBdI5uUK5lV9LWLe5YOstzZurzSIryC6M"

# Инициализация объектов бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# Планировщик для выполнения отложенных задач
scheduler = AsyncIOScheduler()

# Состояния пользователей: хранит текущий шаг и данные для задачи
user_states = {}  # user_id -> {"state": state, "data": task_data}


def main_menu():
    """
    Создает клавиатуру для основного меню.

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками для добавления задач и просмотра списка задач.
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Добавить задачу", callback_data="add_task")],
        [InlineKeyboardButton(text="Посмотреть задачи", callback_data="view_tasks")],
    ])
    return keyboard


def tasks_menu():
    """
    Создает клавиатуру для меню задач.

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками для добавления задачи и возврата в главное меню.
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Добавить задачу", callback_data="add_task")],
        [InlineKeyboardButton(text="Главное меню", callback_data="main_menu")],
    ])
    return keyboard


def cancel_button():
    """
    Создает клавиатуру с кнопкой для отмены операции.

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопкой возврата в главное меню.
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Главное меню", callback_data="main_menu")],
    ])


@router.message(Command("start"))
async def start(message: types.Message):
    """
    Обрабатывает команду /start.

    Args:
        message (types.Message): Сообщение, отправленное пользователем.
    """
    user_states[message.from_user.id] = None
    await message.answer(
        "Привет! Я твой менеджер задач. Выбирай одну из кнопок ниже.",
        reply_markup=main_menu()
    )


@router.callback_query()
async def handle_callbacks(callback: types.CallbackQuery):
    """
    Обрабатывает callback-запросы от пользователя.

    Args:
        callback (types.CallbackQuery): Callback-запрос от пользователя.
    """
    user_id = callback.from_user.id

    if callback.data == "add_task":
        user_states[user_id] = {"state": "waiting_for_name", "data": {}}
        await callback.message.answer("Введите название задачи:", reply_markup=cancel_button())
    elif callback.data == "view_tasks":
        tasks = load_user_tasks(user_id)

        if not tasks:
            await callback.message.answer("У вас нет задач.", reply_markup=tasks_menu())
        else:
            user_states[user_id] = {"state": "viewing_tasks"}
            response = "Ваши задачи:\n"
            for i, task in enumerate(tasks, 1):
                task_id, task_name, deadline, description = task
                response += (f"{i}. <b>{task_name}</b> (ID: {task_id})\n"
                             f"   Дедлайн: <i>{deadline}</i>\n"
                             f"   Описание: {description}\n\n")
            response += "Если хотите удалить задачу, введите её ID ниже."
            await callback.message.answer(response, parse_mode="HTML", reply_markup=tasks_menu())
    elif callback.data == "main_menu":
        user_states[user_id] = None
        await callback.message.answer("Вы вернулись в главное меню.", reply_markup=main_menu())


@router.message()
async def handle_task_creation(message: types.Message):
    """
    Обрабатывает сообщения пользователя для создания и удаления задач.

    Args:
        message (types.Message): Сообщение от пользователя.
    """
    user_id = message.from_user.id
    state = user_states.get(user_id, {}).get("state")

    if state == "waiting_for_name":
        if message.text.lower() == "главное меню":
            user_states[user_id] = None
            await message.answer("Вы вернулись в главное меню.", reply_markup=main_menu())
        else:
            user_states[user_id]["data"]["name"] = message.text
            user_states[user_id]["state"] = "waiting_for_deadline"
            await message.answer("Введите дедлайн задачи в формате ГГГГ-ММ-ДД ЧЧ:ММ:", reply_markup=cancel_button())
    elif state == "waiting_for_deadline":
        if message.text.lower() == "главное меню":
            user_states[user_id] = None
            await message.answer("Вы вернулись в главное меню.", reply_markup=main_menu())
        else:
            try:
                deadline = datetime.strptime(message.text.strip(), "%Y-%m-%d %H:%M")
                user_states[user_id]["data"]["deadline"] = deadline
                user_states[user_id]["state"] = "waiting_for_description"
                await message.answer("Введите описание задачи:", reply_markup=cancel_button())
            except ValueError:
                await message.answer("Неверный формат даты. Попробуйте снова.")
    elif state == "waiting_for_description":
        if message.text.lower() == "главное меню":
            user_states[user_id] = None
            await message.answer("Вы вернулись в главное меню.", reply_markup=main_menu())
        else:
            description = message.text
            task_data = user_states[user_id]["data"]
            user_states[user_id] = None  # Сброс состояния

            add_task(user_id, message.from_user.username or "unknown",
                     task_data["name"], task_data["deadline"].strftime('%Y-%m-%d %H:%M'),
                     description)

            scheduler.add_job(
                notify_user,
                DateTrigger(run_date=task_data["deadline"] - timedelta(days=1)),
                args=[user_id, f"Напоминание: до задачи <b>{task_data['name']}</b> остались сутки!"]
            )
            scheduler.add_job(
                notify_user,
                DateTrigger(run_date=task_data["deadline"] - timedelta(hours=2)),
                args=[user_id, f"Напоминание: до задачи <b>{task_data['name']}</b> осталось 2 часа!"]
            )

            await message.answer(
                f"Задача <b>{task_data['name']}</b> успешно добавлена!",
                parse_mode="HTML",
                reply_markup=main_menu()
            )
    elif message.text.isdigit() and user_states.get(user_id, {}).get("state") == "viewing_tasks":
        try:
            task_id = int(message.text)
            delete_task(task_id)
            await message.answer("Задача успешно удалена.", reply_markup=main_menu())
        except Exception as e:
            await message.answer(f"Ошибка удаления задачи: {e}")
    else:
        await message.answer("Команда не распознана. Используйте кнопки меню.")


async def notify_user(user_id: int, message: str):
    """
    Отправляет пользователю уведомление.

    Args:
        user_id (int): ID пользователя.
        message (str): Сообщение для отправки.
    """
    try:
        await bot.send_message(user_id, message, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Не удалось отправить сообщение: {e}")


async def main():
    """
    Основная функция для запуска бота.
    """
    init_db()
    scheduler.start()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())