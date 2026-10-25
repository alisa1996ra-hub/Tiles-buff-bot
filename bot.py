import os
import logging
import sys
import asyncio
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

# Настройка логов
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logging.error("Токен бота не найден в переменных окружения!")
    sys.exit(1)

router = Router()

# Состояния для FSM (ожидание кастомного ввода)
class CalcState(StatesGroup):
    waiting_for_building_days = State()
    waiting_for_research_days = State()

# --- Клавиатуры ---

def main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏗 Строительство", callback_data="menu_building")],
        [InlineKeyboardButton(text="🔬 Исследования", callback_data="menu_research")]
    ])

def building_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="До 3 дней", callback_data="b_3"),
         InlineKeyboardButton(text="До 5 дней", callback_data="b_5")],
        [InlineKeyboardButton(text="✏️ Свое количество (1-20 дней)", callback_data="b_custom")],
        [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_main")]
    ])

def research_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="10 дней", callback_data="r_10"),
         InlineKeyboardButton(text="15 дней", callback_data="r_15")],
        [InlineKeyboardButton(text="✏️ Свое количество (1-25 дней)", callback_data="r_custom")],
        [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_main")]
    ])

def back_to_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ В главное меню", callback_data="back_main")]
    ])

# --- Логика расчетов (заменишь на свои формулы) ---

def calculate_building(days: int) -> str:
    # Твоя математика баффов для стройки
    hours = days * 24
    return (
        f"🏗 **Расчет для стройки ({days} дн. / {hours} ч.):**\n\n"
        f"• Требуемый суммарный бафф скорости: ...\n"
        f"• Рекомендуемый план ускорителей / помощи союза: ...\n"
        f"*(Здесь подставляются твои алгоритмы)*"
    )

def calculate_research(days: int) -> str:
    # Твоя математика баффов для исследований
    hours = days * 24
    return (
        f"🔬 **Расчет для исследований ({days} дн. / {hours} ч.):**\n\n"
        f"• Оптимальный тайминг под ковровые баффы: ...\n"
        f"• Необходимый процент снижения времени: ...\n"
        f"*(Здесь подставляются твои алгоритмы)*"
    )

# --- Хэндлеры (Обработчики) ---

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🤖 **Калькулятор баффов альянса запущен.**\n\n"
        "Выбери категорию задачи:",
        reply_markup=main_menu_kb(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "back_main")
async def cb_back_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "Выбери категорию задачи:",
        reply_markup=main_menu_kb()
    )
    await callback.answer()

@router.callback_query(F.data == "menu_building")
async def cb_building_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "🏗 **Категория: Строительство**\nВыберите фиксированный вариант или введите свое значение:",
        reply_markup=building_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "menu_research")
async def cb_research_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "🔬 **Категория: Исследования**\nВыберите фиксированный вариант или введите свое значение:",
        reply_markup=research_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()

# Обработка фиксированных кнопок стройки
@router.callback_query(F.data.in_({"b_3", "b_5"}))
async def cb_building_fixed(callback: CallbackQuery):
    days = 3 if callback.data == "b_3" else 5
    result_text = calculate_building(days)
    await callback.message.edit_text(result_text, reply_markup=back_to_menu_kb(), parse_mode="Markdown")
    await callback.answer()

# Обработка фиксированных кнопок исследований
@router.callback_query(F.data.in_({"r_10", "r_15"}))
async def cb_research_fixed(callback: CallbackQuery):
    days = 10 if callback.data == "r_10" else 15
    result_text = calculate_research(days)
    await callback.message.edit_text(result_text, reply_markup=back_to_menu_kb(), parse_mode="Markdown")
    await callback.answer()

# Запрос кастомного ввода для стройки (1-20)
@router.callback_query(F.data == "b_custom")
async def cb_building_custom_prompt(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CalcState.waiting_for_building_days)
    await callback.message.edit_text(
        "✏️ Введите количество дней для **стройки** (число от 1 до 20):",
        parse_mode="Markdown"
    )
    await callback.answer()

# Обработка ввода цифры для стройки
@router.message(CalcState.waiting_for_building_days)
async def process_building_custom(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Пожалуйста, введите целое число от 1 до 20.")
        return
    
    days = int(message.text)
    if not (1 <= days <= 20):
        await message.answer("⚠️ Число должно быть в диапазоне от 1 до 20. Попробуйте еще раз:")
        return

    await state.clear()
    result_text = calculate_building(days)
    await message.answer(result_text, reply_markup=back_to_menu_kb(), parse_mode="Markdown")

# Запрос кастомного ввода для исследований (1-25)
@router.callback_query(F.data == "r_custom")
async def cb_research_custom_prompt(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CalcState.waiting_for_research_days)
    await callback.message.edit_text(
        "✏️ Введите количество дней для **исследований** (число от 1 до 25):",
        parse_mode="Markdown"
    )
    await callback.answer()

# Обработка ввода цифры для исследований
@router.message(CalcState.waiting_for_research_days)
async def process_research_custom(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Пожалуйста, введите целое число от 1 до 25.")
        return
    
    days = int(message.text)
    if not (1 <= days <= 25):
        await message.answer("⚠️ Число должно быть в диапазоне от 1 до 25. Попробуйте еще раз:")
        return

    await state.clear()
    result_text = calculate_research(days)
    await message.answer(result_text, reply_markup=back_to_menu_kb(), parse_mode="Markdown")

# --- Запуск ---
async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Бот запущен и готов принимать задачи!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
