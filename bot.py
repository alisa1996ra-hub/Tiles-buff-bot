import os
import logging
import sys
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

# Настройка логирования
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logging.error("Токен бота не найден в переменных окружения!")
    sys.exit(1)

# --- Фоновый HTTP-сервер для Health Check на Render ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Tiles Timer Calc Bot is active 24/7!")
        
    def log_message(self, format, *args):
        return

def run_health_server():
    port = int(os.getenv("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    logging.info(f"Health-check server started on port {port}")
    server.serve_forever()

threading.Thread(target=run_health_server, daemon=True).start()
# -----------------------------------------------------

router = Router()

# Состояния FSM
class CalcState(StatesGroup):
    waiting_for_timer = State()

# --- Клавиатуры ---

def main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏗 Строительство", callback_data="cat_building")],
        [InlineKeyboardButton(text="🔬 Исследования", callback_data="cat_research")]
    ])

def building_targets_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Цель: до 3 дней", callback_data="target_b_3"),
         InlineKeyboardButton(text="Цель: до 5 дней", callback_data="target_b_5")],
        [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_main")]
    ])

def research_targets_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Цель: до 10 дней", callback_data="target_r_10"),
         InlineKeyboardButton(text="Цель: до 15 дней", callback_data="target_r_15")],
        [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_main")]
    ])

# --- Математический движок расчета таймеров ---
def calculate_buffs(source_days: float, target_days: float) -> tuple[int, float]:
    current = source_days
    buffs_count = 0
    # Каждое применение уменьшает таймер на 15% (множитель 0.85)
    while current > target_days and buffs_count < 10000:
        current *= (1 - 0.15)
        buffs_count += 1
    return buffs_count, round(current, 2)

# --- Хэндлеры ---

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "⏳ **Калькулятор редукции таймеров**\n\nВыбери тип задачи:",
        reply_markup=main_menu_kb(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "back_main")
async def cb_back_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "⏳ **Калькулятор редукции таймеров**\n\nВыбери тип задачи:",
        reply_markup=main_menu_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "cat_building")
async def cb_building(callback: CallbackQuery, state: FSMContext):
    await state.update_data(mode="Строительство")
    await callback.message.edit_text(
        "🏗 **Режим: строительство**\nВыберите целевой порог дней:",
        reply_markup=building_targets_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "cat_research")
async def cb_research(callback: CallbackQuery, state: FSMContext):
    await state.update_data(mode="Исследования")
    await callback.message.edit_text(
        "🔬 **Режим: исследования**\nВыберите целевой порог дней:",
        reply_markup=research_targets_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("target_"))
async def cb_set_target(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    target_val = float(parts[2])
    
    await state.update_data(target=target_val)
    await state.set_state(CalcState.waiting_for_timer)
    
    data = await state.get_data()
    mode_name = data.get("mode", "Задача")
    
    await callback.message.edit_text(
        f"⏳ Режим: {mode_name.lower()} (цель: до {target_val:g} дн.).\n\n"
        f"Введите текущее время таймера в днях:",
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(CalcState.waiting_for_timer)
async def process_timer_input(message: Message, state: FSMContext):
    text = message.text.replace(",", ".")
    try:
        source_days = float(text)
        if source_days <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("⚠️ Введите корректное число (например, `500` или `1000`):", parse_mode="Markdown")
        return

    data = await state.get_data()
    mode = data.get("mode", "Задача")
    target = data.get("target", 3.0)

    buffs, remainder = calculate_buffs(source_days, target)
    await state.clear()

    result_text = (
        f"📊 **Результат ({mode}):**\n"
        f"• Исходник: {source_days} дн.\n"
        f"• Цель: {target:g} дн.\n"
        f"• Баффов нужно (-15%): 🧩 {buffs} шт.\n"
        f"• Остаток: {remainder} дн.\n\n"
        f"🔄 /start для нового расчета."
    )

    await message.answer(result_text, parse_mode="Markdown")

# --- Запуск ---
async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Бот успешно запущен в облаке!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
