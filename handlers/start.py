from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from storage import storage
from keyboards.inline import main_menu_kb
from utils.message_manager import send_or_edit, edit_current, delete_user_message, set_last_message_id

router = Router()

WELCOME_TEXT = """
🎮 <b>Ласкаво просимо до гри!</b>

Це бот для організації командної гри в гуртожитку.

<b>Як це працює:</b>
1️⃣ Приєднайся до команди
2️⃣ Збери команду з 5 людей
3️⃣ Чекай на старт гри від адміністратора
4️⃣ Коли гра почнеться — прийди до палатки за 4 хвилини!

Обери дію нижче 👇
"""

RULES_TEXT = """
📜 <b>Правила гри</b>

1️⃣ Кожна команда складається максимум з <b>5 гравців</b>
2️⃣ Один гравець може бути тільки в <b>одній команді</b>
3️⃣ Капітан команди може <b>кікати</b> учасників
4️⃣ Якщо капітан виходить — команда <b>розпускається</b>
5️⃣ Коли адмін запускає гру — у вас є <b>4 хвилини</b> щоб прийти до палатки
6️⃣ Палатка — це наша <b>локація для івентів</b>

🏕️ <b>Будьте готові та не пропустіть сповіщення!</b>
"""


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    """Обробник команди /start."""
    user = message.from_user
    # Реєструємо гравця
    storage.add_player(
        user_id=user.id,
        username=user.username or "",
        full_name=user.full_name or "Невідомий",
    )
    is_admin = storage.is_admin(user.id)
    # Видаляємо команду /start
    await delete_user_message(bot, message.chat.id, message.message_id)
    # Надсилаємо єдине активне повідомлення
    await send_or_edit(bot, message.chat.id, WELCOME_TEXT, reply_markup=main_menu_kb())


@router.callback_query(F.data == "back_menu")
async def back_to_menu(callback: CallbackQuery, bot: Bot):
    """Повернутися в головне меню."""
    await edit_current(bot, callback.message.chat.id, WELCOME_TEXT, reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "rules")
async def show_rules(callback: CallbackQuery, bot: Bot):
    """Показати правила гри."""
    from keyboards.inline import InlineKeyboardMarkup, InlineKeyboardButton

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_menu")]
        ]
    )
    await edit_current(bot, callback.message.chat.id, RULES_TEXT, reply_markup=kb)
    await callback.answer()
