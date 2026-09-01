import asyncio
import logging
import sys
import io
import socket
from typing import Any, Awaitable, Callable
import aiohttp

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Message, TelegramObject
from aiogram.dispatcher.middlewares.base import BaseMiddleware

from config import BOT_TOKEN
from handlers import start_router, teams_router, admin_router, game_router


class CustomTelegramResolver(aiohttp.DefaultResolver):
    """Спеціальний резолвер для обходу проблем з локальним DNS/VPN на Windows."""
    async def resolve(self, host, port=0, family=socket.AF_INET):
        if host == "api.telegram.org":
            return [
                {
                    "hostname": host,
                    "host": "149.154.166.110",
                    "port": port,
                    "family": socket.AF_INET,
                    "proto": 0,
                    "flags": 0,
                }
            ]
        return await super().resolve(host, port, family)


class CustomAiohttpSession(AiohttpSession):
    """AiohttpSession із власно налаштованим конектором для Telegram."""
    async def create_session(self) -> aiohttp.ClientSession:
        return aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(resolver=CustomTelegramResolver()),
            json_serialize=self.json_dumps,
        )


# Логування (з підтримкою UTF-8 на Windows)
handler = logging.StreamHandler(
    stream=io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
)
handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logging.basicConfig(level=logging.INFO, handlers=[handler])
logger = logging.getLogger(__name__)


class DismissOldMessageMiddleware(BaseMiddleware):
    """
    Мідлвеар: автоматично видаляє (або прибирає кнопки з) попереднє бот-повідомлення
    при надходженні будь-якої команди (/start, /admin тощо).
    Це унеможливлює появу двох меню одночасно.
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.text and event.text.startswith("/"):
            bot: Bot = data["bot"]
            from utils.message_manager import dismiss_old_message
            await dismiss_old_message(bot, event.chat.id)
        return await handler(event, data)


async def main():
    """Точка входу бота."""
    if not BOT_TOKEN:
        logger.error(
            "BOT_TOKEN не вказано! "
            "Створи файл .env та додай BOT_TOKEN=your_token_here"
        )
        return

    # Ініціалізація кастомної сесії з надійним резолвером IP
    session = CustomAiohttpSession()

    # Ініціалізація бота
    bot = Bot(
        token=BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # Диспетчер з FSM сховищем в пам'яті
    dp = Dispatcher(storage=MemoryStorage())

    # Мідлвеар: автоматично прибирає старе бот-повідомлення при будь-якій команді
    dp.message.middleware(DismissOldMessageMiddleware())

    # Підключаємо роутери (порядок має значення!)
    dp.include_router(admin_router)   # Адмін-панель
    dp.include_router(start_router)   # /start та головне меню
    dp.include_router(teams_router)   # Управління командами
    dp.include_router(game_router)    # Ігрова логіка

    logger.info("Bot starting...")

    while True:
        try:
            # Видаляємо старі webhook та запускаємо polling
            await bot.delete_webhook(drop_pending_updates=True)
            await dp.start_polling(bot)
            break
        except Exception as e:
            logger.warning(f"Connection error ({e}), retrying in 5 seconds...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
