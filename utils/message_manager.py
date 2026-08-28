"""
utils/message_manager.py

Менеджер повідомлень: зберігає ID останнього бот-повідомлення для кожного
користувача в постійному сховищі (JSON) і видаляє його перед надсиланням нового.
Це дає ефект «одного вікна» — навіть після перезапуску бота старе повідомлення
буде знайдено і видалено.
"""
from __future__ import annotations

import logging
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup

logger = logging.getLogger(__name__)


def _get_storage():
    """Lazy import щоб уникнути циклічних залежностей."""
    from storage import storage
    return storage


async def _try_delete(bot: Bot, chat_id: int, message_id: int) -> bool:
    """Спробувати видалити повідомлення. Повертає True якщо вдалося."""
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        return True
    except Exception:
        return False


async def send_or_edit(
    bot: Bot,
    chat_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str = "HTML",
) -> None:
    """
    Видаляє попереднє бот-повідомлення і надсилає нове.
    ID нового повідомлення зберігається в постійному сховищі.
    """
    store = _get_storage()
    old_id = store.get_bot_message(chat_id)

    # Видаляємо попереднє повідомлення якщо є
    if old_id:
        await _try_delete(bot, chat_id, old_id)
        store.clear_bot_message(chat_id)

    # Надсилаємо нове
    sent = await bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
        parse_mode=parse_mode,
    )
    store.save_bot_message(chat_id, sent.message_id)


async def edit_current(
    bot: Bot,
    chat_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str = "HTML",
) -> None:
    """
    Намагається відредагувати поточне повідомлення на місці (без мерехтіння).
    Якщо редагування не вдається — видаляє старе і надсилає нове.
    """
    store = _get_storage()
    old_id = store.get_bot_message(chat_id)

    if old_id:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=old_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
            return  # Успішно відредаговано — виходимо
        except Exception:
            pass  # Повідомлення не можна редагувати — відправимо нове

    # Fallback: видалити і надіслати нове
    await send_or_edit(bot, chat_id, text, reply_markup, parse_mode)


async def delete_user_message(bot: Bot, chat_id: int, message_id: int) -> None:
    """Видаляє повідомлення користувача (команди, текстовий ввід тощо)."""
    await _try_delete(bot, chat_id, message_id)


def set_last_message_id(chat_id: int, message_id: int) -> None:
    """Вручну встановити ID останнього повідомлення (напр. після answer())."""
    store = _get_storage()
    store.save_bot_message(chat_id, message_id)
