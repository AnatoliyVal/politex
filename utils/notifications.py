import asyncio
from aiogram import Bot
from storage import Storage


async def notify_all_players(bot: Bot, storage: Storage, text: str):
    """Надіслати повідомлення всім зареєстрованим гравцям."""
    player_ids = storage.get_all_player_ids()
    success = 0
    failed = 0

    for user_id in player_ids:
        try:
            await bot.send_message(user_id, text, parse_mode="HTML")
            success += 1
        except Exception:
            failed += 1
        # Невелика затримка щоб не потрапити під ліміт Telegram
        await asyncio.sleep(0.05)

    return success, failed


async def notify_team(bot: Bot, storage: Storage, team_id: str, text: str):
    """Надіслати повідомлення всій команді."""
    team = storage.get_team(team_id)
    if not team:
        return 0, 0

    success = 0
    failed = 0

    for member_id in team["members"]:
        try:
            await bot.send_message(member_id, text, parse_mode="HTML")
            success += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)

    return success, failed


async def start_countdown(bot: Bot, storage: Storage, minutes: int):
    """Запустити таймер зворотного відліку.

    Надсилає проміжні повідомлення та фінальне коли час вийде.
    """
    total_seconds = minutes * 60

    # Проміжні сповіщення
    checkpoints = []
    if total_seconds > 120:
        checkpoints.append(120)  # 2 хвилини
    if total_seconds > 60:
        checkpoints.append(60)   # 1 хвилина
    checkpoints.append(30)       # 30 секунд

    elapsed = 0
    checkpoint_idx = 0

    # Сортуємо контрольні точки: скільки секунд залишилось
    remaining_alerts = sorted(checkpoints, reverse=True)

    for alert_time in remaining_alerts:
        wait_until = total_seconds - alert_time
        if wait_until > elapsed:
            await asyncio.sleep(wait_until - elapsed)
            elapsed = wait_until

            mins = alert_time // 60
            secs = alert_time % 60
            if mins > 0:
                time_str = f"{mins} хв {secs:02d} сек" if secs else f"{mins} хв"
            else:
                time_str = f"{secs} сек"

            await notify_all_players(
                bot,
                storage,
                f"⏰ <b>Залишилось {time_str}!</b>\n\n"
                f"🏕️ Біжіть до палатки! 🏃‍♂️",
            )

    # Чекаємо решту часу
    remaining = total_seconds - elapsed
    if remaining > 0:
        await asyncio.sleep(remaining)

    # Час вийшов!
    await notify_all_players(
        bot,
        storage,
        "🔔 <b>ЧАС ВИЙШОВ!</b>\n\n"
        "⏰ 4 хвилини минули!\n"
        "🏕️ Всі мають бути біля палатки!\n\n"
        "🎮 Гра починається!",
    )
