import asyncio
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from storage import storage
from config import ADMIN_PASSWORD, TIMER_MINUTES
from keyboards.inline import admin_panel_kb, confirm_kb, back_to_admin_kb, score_teams_kb, admin_teams_kb
from keyboards.inline import InlineKeyboardMarkup, InlineKeyboardButton
from utils.notifications import notify_all_players, start_countdown
from utils.message_manager import send_or_edit, edit_current, delete_user_message, set_last_message_id

router = Router()


class AdminStates(StatesGroup):
    """ФСМ стани для адмін-панелі."""
    waiting_for_password = State()
    waiting_for_announcement = State()
    waiting_for_score = State()


# ── Вхід в адмін-панель ────────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext, bot: Bot):
    """Команда /admin — вхід в адмін-панель."""
    await state.clear()
    # Видаляємо команду /admin
    await delete_user_message(bot, message.chat.id, message.message_id)

    if storage.is_admin(message.from_user.id):
        status = storage.get_game_status()
        await send_or_edit(
            bot,
            message.chat.id,
            "⚙️ <b>Адмін-панель</b>\n\nОбери дію:",
            reply_markup=admin_panel_kb(status),
        )
        return

    await send_or_edit(
        bot,
        message.chat.id,
        "🔐 <b>Вхід в адмін-панель</b>\n\nВведи пароль:",
    )
    await state.set_state(AdminStates.waiting_for_password)


@router.message(AdminStates.waiting_for_password)
async def check_admin_password(message: Message, state: FSMContext, bot: Bot):
    """Перевірка пароля адміна."""
    # Видаляємо повідомлення з паролем
    await delete_user_message(bot, message.chat.id, message.message_id)

    if message.text == ADMIN_PASSWORD:
        storage.add_admin(message.from_user.id)
        status = storage.get_game_status()
        await send_or_edit(
            bot,
            message.chat.id,
            "✅ <b>Пароль вірний!</b>\n\n⚙️ <b>Адмін-панель</b>\n\nОбери дію:",
            reply_markup=admin_panel_kb(status),
        )
    else:
        await send_or_edit(
            bot,
            message.chat.id,
            "❌ Невірний пароль. Спробуй ще раз:",
        )
        await state.set_state(AdminStates.waiting_for_password)
        return

    await state.clear()


# ── Повернення до адмін-панелі ─────────────────────────────

@router.callback_query(F.data == "admin_panel")
async def show_admin_panel(callback: CallbackQuery, bot: Bot):
    """Показати адмін-панель."""
    if not storage.is_admin(callback.from_user.id):
        await callback.answer("❌ Ти не адмін!", show_alert=True)
        return

    status = storage.get_game_status()
    await edit_current(
        bot,
        callback.message.chat.id,
        "⚙️ <b>Адмін-панель</b>\n\nОбери дію:",
        reply_markup=admin_panel_kb(status),
    )
    await callback.answer()


# ── Статус гри ──────────────────────────────────────────────

@router.callback_query(F.data == "admin_status")
async def admin_status(callback: CallbackQuery, bot: Bot):
    """Показати статистику гри."""
    if not storage.is_admin(callback.from_user.id):
        await callback.answer("❌ Ти не адмін!", show_alert=True)
        return

    stats = storage.get_stats()
    status_emoji = {
        "registration": "📝 Реєстрація",
        "active": "🎮 Гра активна",
        "finished": "⏸️ Раунд завершено (очікує балів/наступного раунду)",
        "game_over": "🏁 Гра завершена (Фінал)",
    }

    text = (
        f"📊 <b>Статистика гри</b>\n\n"
        f"📌 Статус: {status_emoji.get(stats['game_status'], stats['game_status'])}\n"
        f"🚩 Раунд: #{stats.get('round', 0)}\n"
        f"👥 Всього гравців: {stats['total_players']}\n"
        f"🏗️ Команд: {stats['total_teams']}\n"
        f"✅ В командах: {stats['players_in_teams']}\n"
        f"❌ Без команди: {stats['players_without_team']}"
    )

    await edit_current(bot, callback.message.chat.id, text, reply_markup=back_to_admin_kb())
    await callback.answer()


# ── Список команд ──────────────────────────────────────────

@router.callback_query(F.data == "admin_teams")
async def admin_teams(callback: CallbackQuery, bot: Bot):
    """Показати всі команди."""
    if not storage.is_admin(callback.from_user.id):
        await callback.answer("❌ Ти не адмін!", show_alert=True)
        return

    teams = storage.get_all_teams()
    if not teams:
        await edit_current(
            bot,
            callback.message.chat.id,
            "👥 <b>Команди</b>\n\n😔 Поки що немає жодної команди.",
            reply_markup=back_to_admin_kb(),
        )
        await callback.answer()
        return

    lines = ["👥 <b>Список команд</b>\n"]
    for team_id, team in teams.items():
        members_names = []
        for mid in team["members"]:
            player = storage.get_player(mid)
            name = player["full_name"] if player else "?"
            if mid == team["captain_id"]:
                name = f"👑{name}"
            members_names.append(name)

        members_str = ", ".join(members_names) if members_names else "немає учасників"
        lines.append(
            f"\n🏷️ <b>{team['name']}</b> ({len(team['members'])}/5)\n"
            f"   {members_str}\n"
            f"   🔑 <code>{team_id}</code>"
        )

    await edit_current(
        bot,
        callback.message.chat.id,
        "\n".join(lines),
        reply_markup=admin_teams_kb(teams),
    )
    await callback.answer()


# ── Видалення команди (адмін) ──────────────────────────────

@router.callback_query(F.data.startswith("admin_delete_team_"))
async def admin_delete_team_confirm(callback: CallbackQuery, bot: Bot):
    """Підтвердження видалення команди."""
    if not storage.is_admin(callback.from_user.id):
        await callback.answer("❌ Ти не адмін!", show_alert=True)
        return

    team_id = callback.data.replace("admin_delete_team_", "")
    team = storage.get_team(team_id)
    if not team:
        await callback.answer("❌ Команду не знайдено!", show_alert=True)
        return

    members_count = len(team["members"])
    await edit_current(
        bot,
        callback.message.chat.id,
        f"🗑️ <b>Видалити команду «{team['name']}»?</b>\n\n"
        f"👥 Учасників: {members_count}\n"
        "⚠️ Всі учасники будуть відписані від команди!",
        reply_markup=confirm_kb(f"deleteteam_{team_id}"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_deleteteam_"))
async def admin_delete_team(callback: CallbackQuery, bot: Bot):
    """Видалення команди."""
    if not storage.is_admin(callback.from_user.id):
        await callback.answer("❌ Ти не адмін!", show_alert=True)
        return

    team_id = callback.data.replace("confirm_deleteteam_", "")
    success, msg = storage.delete_team(team_id)

    teams = storage.get_all_teams()
    if teams:
        await edit_current(
            bot,
            callback.message.chat.id,
            f"{msg}\n\n👥 <b>Список команд</b> оновлено.",
            reply_markup=admin_teams_kb(teams),
        )
    else:
        await edit_current(
            bot,
            callback.message.chat.id,
            f"{msg}\n\n😔 Команд більше немає.",
            reply_markup=back_to_admin_kb(),
        )
    await callback.answer()


@router.callback_query(F.data == "noop")
async def noop_handler(callback: CallbackQuery):
    """Інформаційна кнопка (нічого не робить)."""
    await callback.answer()


# ── Почати гру ──────────────────────────────────────────────

@router.callback_query(F.data == "admin_start_game")
async def admin_start_game_confirm(callback: CallbackQuery, bot: Bot):
    """Підтвердження старту гри."""
    if not storage.is_admin(callback.from_user.id):
        await callback.answer("❌ Ти не адмін!", show_alert=True)
        return

    teams = storage.get_all_teams()
    if len(teams) < 2:
        await callback.answer(
            "❌ Потрібно мінімум 2 команди щоб почати гру!",
            show_alert=True,
        )
        return

    stats = storage.get_stats()
    await edit_current(
        bot,
        callback.message.chat.id,
        f"🚀 <b>Почати гру?</b>\n\n"
        f"👥 Команд: {stats['total_teams']}\n"
        f"👤 Гравців: {stats['players_in_teams']}\n\n"
        f"⏰ Буде запущено таймер на {TIMER_MINUTES} хв.",
        reply_markup=confirm_kb("start_game"),
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_start_game")
async def admin_start_game(callback: CallbackQuery, bot: Bot):
    """Запуск гри."""
    if not storage.is_admin(callback.from_user.id):
        await callback.answer("❌ Ти не адмін!", show_alert=True)
        return

    storage.set_game_status("active")

    # Сповіщення всім гравцям
    game_text = (
        "🎮 <b>ГРА ПОЧИНАЄТЬСЯ!</b>\n\n"
        f"⏰ У вас є <b>{TIMER_MINUTES} хвилини</b> щоб прийти до нашої палатки!\n\n"
        "🏕️ <b>Біжіть до палатки!</b>\n\n"
        f"⏳ Таймер: {TIMER_MINUTES}:00"
    )

    success, failed = await notify_all_players(bot, storage, game_text)

    await edit_current(
        bot,
        callback.message.chat.id,
        f"✅ <b>Гру запущено!</b>\n\n"
        f"📨 Сповіщення надіслано!\n"
        f"✅ Успішно: {success} | ❌ Невдало: {failed}",
        reply_markup=back_to_admin_kb(),
    )

    # Запускаємо таймер у фоні
    asyncio.create_task(start_countdown(bot, storage, TIMER_MINUTES))
    await callback.answer()


# ── Завершити раунд ─────────────────────────────────────

@router.callback_query(F.data == "admin_stop_game")
async def admin_stop_game_confirm(callback: CallbackQuery, bot: Bot):
    """Підтвердження завершення раунду."""
    if not storage.is_admin(callback.from_user.id):
        await callback.answer("❌ Ти не адмін!", show_alert=True)
        return

    round_num = storage.get_round()
    await edit_current(
        bot,
        callback.message.chat.id,
        f"⏹️ <b>Завершити раунд #{round_num}?</b>\n\n"
        "Після завершення можна буде виставити бали командам.",
        reply_markup=confirm_kb("stop_game"),
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_stop_game")
async def admin_stop_game(callback: CallbackQuery, bot: Bot):
    """Завершення раунду."""
    if not storage.is_admin(callback.from_user.id):
        await callback.answer("❌ Ти не адмін!", show_alert=True)
        return

    round_num = storage.get_round()
    storage.set_game_status("finished")

    await notify_all_players(
        bot,
        storage,
        f"🏁 <b>Раунд #{round_num} завершено!</b>\n\n"
        "Чекайте на результати та наступний раунд! 🌟",
    )

    status = storage.get_game_status()
    await edit_current(
        bot,
        callback.message.chat.id,
        f"✅ <b>Раунд #{round_num} завершено!</b>\n\n"
        "Тепер можна виставити бали командам або запустити наступний раунд.",
        reply_markup=admin_panel_kb(status),
    )
    await callback.answer()


# ── Виставлення балів ───────────────────────────────────

@router.callback_query(F.data == "admin_set_scores")
async def admin_set_scores(callback: CallbackQuery, bot: Bot):
    """Показати список команд для виставлення балів."""
    if not storage.is_admin(callback.from_user.id):
        await callback.answer("❌ Ти не адмін!", show_alert=True)
        return

    teams = storage.get_all_teams()
    if not teams:
        await callback.answer("❌ Немає команд!", show_alert=True)
        return

    await edit_current(
        bot,
        callback.message.chat.id,
        "⭐ <b>Виставлення балів</b>\n\nОбери команду, якій хочеш додати бали:",
        reply_markup=score_teams_kb(teams),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("score_"))
async def admin_score_team(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Обрати команду та ввести бали."""
    if not storage.is_admin(callback.from_user.id):
        await callback.answer("❌ Ти не адмін!", show_alert=True)
        return

    team_id = callback.data.replace("score_", "")
    team = storage.get_team(team_id)
    if not team:
        await callback.answer("❌ Команду не знайдено!", show_alert=True)
        return

    current_score = team.get("score", 0)
    await edit_current(
        bot,
        callback.message.chat.id,
        f"⭐ <b>Бали для команди «{team['name']}»</b>\n\n"
        f"📊 Поточні бали: <b>{current_score}</b>\n\n"
        "Введи кількість балів для додавання\n"
        "(додатне число додасть, від'ємне відніме):",
    )
    await state.set_state(AdminStates.waiting_for_score)
    await state.update_data(scoring_team_id=team_id)
    await callback.answer()


@router.message(AdminStates.waiting_for_score)
async def admin_score_input(message: Message, state: FSMContext, bot: Bot):
    """Обробка введення балів."""
    # Видаляємо повідомлення адміна
    await delete_user_message(bot, message.chat.id, message.message_id)

    try:
        points = int(message.text.strip())
    except (ValueError, AttributeError):
        await send_or_edit(bot, message.chat.id, "❌ Введи число! Наприклад: 10, -5, 100")
        return

    data = await state.get_data()
    team_id = data.get("scoring_team_id")
    team = storage.get_team(team_id)

    if not team:
        await send_or_edit(bot, message.chat.id, "❌ Команду не знайдено!")
        await state.clear()
        return

    storage.add_score(team_id, points)
    new_score = storage.get_team(team_id).get("score", 0)
    sign = "+" if points >= 0 else ""

    teams = storage.get_all_teams()
    await send_or_edit(
        bot,
        message.chat.id,
        f"✅ Команді <b>«{team['name']}»</b> {sign}{points} балів!\n"
        f"📊 Загалом: <b>{new_score}</b>\n\n"
        "Обери наступну команду або повернись до панелі:",
        reply_markup=score_teams_kb(teams),
    )
    await state.clear()


# ── Наступний раунд ───────────────────────────────────

@router.callback_query(F.data == "admin_next_round")
async def admin_next_round_confirm(callback: CallbackQuery, bot: Bot):
    """Підтвердження старту наступного раунду."""
    if not storage.is_admin(callback.from_user.id):
        await callback.answer("❌ Ти не адмін!", show_alert=True)
        return

    next_round = storage.get_round() + 1
    await edit_current(
        bot,
        callback.message.chat.id,
        f"▶️ <b>Запустити раунд #{next_round}?</b>\n\n"
        "Всім гравцям буде надіслано сповіщення.",
        reply_markup=confirm_kb("next_round"),
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_next_round")
async def admin_next_round(callback: CallbackQuery, bot: Bot):
    """Запуск наступного раунду (без таймера)."""
    if not storage.is_admin(callback.from_user.id):
        await callback.answer("❌ Ти не адмін!", show_alert=True)
        return

    storage.set_game_status("active")
    round_num = storage.get_round()

    game_text = (
        f"🎮 <b>Раунд #{round_num} починається!</b>\n\n"
        "🏕️ Готуйтеся! 💪"
    )

    success, failed = await notify_all_players(bot, storage, game_text)

    await edit_current(
        bot,
        callback.message.chat.id,
        f"✅ <b>Раунд #{round_num} запущено!</b>\n\n"
        f"📨 Успішно: {success} | ❌ Невдало: {failed}",
        reply_markup=admin_panel_kb("active"),
    )
    await callback.answer()


# ── Завершити ГРУ (Фінал) ───────────────────────────────────

@router.callback_query(F.data == "admin_finish_game")
async def admin_finish_game_confirm(callback: CallbackQuery, bot: Bot):
    """Підтвердження завершення всієї гри."""
    if not storage.is_admin(callback.from_user.id):
        await callback.answer("❌ Ти не адмін!", show_alert=True)
        return

    await edit_current(
        bot,
        callback.message.chat.id,
        "🏁 <b>Завершити ГРУ та оголосити фінальні результати?</b>\n\n"
        "🔥 Усім гравцям буде надіслано підсумковий рейтинг з урочистим привітанням переможців!",
        reply_markup=confirm_kb("finish_game"),
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_finish_game")
async def admin_finish_game(callback: CallbackQuery, bot: Bot):
    """Завершення всієї гри та оголошення підсумків."""
    if not storage.is_admin(callback.from_user.id):
        await callback.answer("❌ Ти не адмін!", show_alert=True)
        return

    storage.set_game_status("game_over")
    leaderboard = storage.get_leaderboard()

    if not leaderboard:
        await edit_current(
            bot,
            callback.message.chat.id,
            "❌ Немає команд для підведення підсумків!",
            reply_markup=back_to_admin_kb(),
        )
        return

    lines = [
        "🏁 <b>УВАГА! ГРУ ОФІЦІЙНО ЗАВЕРШЕНО!</b> 🏁\n",
        "🏆 <b>ПІДСУМКОВИЙ РЕЙТИНГ ТА ПЕРЕМОЖЦІ:</b> 🏆",
        "🎉 🥳 🍾 👑 🎈 🎊 💥 ✨ ✨ ✨\n",
    ]

    for i, (team_id, name, score) in enumerate(leaderboard):
        if i == 0:
            lines.append(
                f"🥇 <b>1-ШЕ МІСЦЕ — КОМАНДА «{name}»!</b> ({score} балів)\n"
                f"👑 <b>ЧЕМПІОНИ НАШОГО ЧЕЛЕНДЖУ!</b> 👑\n"
                f"🥳 <b>ВІТАЄМО З АБСОЛЮТНОЮ ПЕРЕМОГОЮ!</b> 🥳\n"
                f"<i>Ви показали неймовірну згуртованість, швидкість та справжній командний дух! Палатка пишається своїми чемпіонами!</i> 🍾🎉🎈💥✨🎁🎊\n"
            )
        elif i == 1:
            lines.append(f"🥈 <b>2-ге місце:</b> «{name}» — <b>{score}</b> балів! 👏✨⚡")
        elif i == 2:
            lines.append(f"🥉 <b>3-тє місце:</b> «{name}» — <b>{score}</b> балів! 👏✨💫")
        else:
            lines.append(f"  {i+1}. «{name}» — <b>{score}</b> балів 🎯")

    lines.append("\n🏕️ <b>ДЯКУЄМО ВСІМ УЧАСНИКАМ ЗА КРУТУ ГРУ ТА ШАЛЕНІ ЕМОЦІЇ!</b> ❤️🔥🚀")

    final_text = "\n".join(lines)
    success, failed = await notify_all_players(bot, storage, final_text)

    status = storage.get_game_status()
    await edit_current(
        bot,
        callback.message.chat.id,
        f"✅ <b>Гру завершено та підсумки оголошено!</b>\n\n"
        f"📨 Надіслано гравцям: {success}\n"
        f"❌ Невдало: {failed}",
        reply_markup=admin_panel_kb(status),
    )
    await callback.answer()


# ── Рейтинг команд ───────────────────────────────────

@router.callback_query(F.data == "leaderboard")
async def show_leaderboard(callback: CallbackQuery, bot: Bot):
    """Показати рейтинг команд."""
    leaderboard = storage.get_leaderboard()

    if not leaderboard:
        await callback.answer("😔 Поки немає команд!", show_alert=True)
        return

    medals = ["🥇", "🥈", "🥉"]
    lines = ["🏆 <b>Рейтинг команд</b>\n"]

    for i, (team_id, name, score) in enumerate(leaderboard):
        medal = medals[i] if i < 3 else f"  {i+1}."
        lines.append(f"{medal} <b>{name}</b> — {score} балів")

    buttons = []
    if storage.is_admin(callback.from_user.id):
        buttons.append(
            [InlineKeyboardButton(text="🔙 Адмін-панель", callback_data="admin_panel")]
        )
    buttons.append(
        [InlineKeyboardButton(text="🔙 Меню", callback_data="back_menu")]
    )
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await edit_current(bot, callback.message.chat.id, "\n".join(lines), reply_markup=kb)
    await callback.answer()


# ── Надіслати оголошення ────────────────────────────────────

@router.callback_query(F.data == "admin_announce")
async def admin_announce_start(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Почати надсилання оголошення."""
    if not storage.is_admin(callback.from_user.id):
        await callback.answer("❌ Ти не адмін!", show_alert=True)
        return

    await edit_current(
        bot,
        callback.message.chat.id,
        "🔔 <b>Оголошення</b>\n\nНапиши текст оголошення і я надішлю його всім гравцям:",
    )
    await state.set_state(AdminStates.waiting_for_announcement)
    await callback.answer()


@router.message(AdminStates.waiting_for_announcement)
async def admin_announce_send(message: Message, state: FSMContext, bot: Bot):
    """Надіслати оголошення всім."""
    # Видаляємо повідомлення адміна
    await delete_user_message(bot, message.chat.id, message.message_id)

    text = (
        f"📢 <b>Оголошення від адміна:</b>\n\n"
        f"{message.text}"
    )

    success, failed = await notify_all_players(bot, storage, text)

    status = storage.get_game_status()
    await send_or_edit(
        bot,
        message.chat.id,
        f"✅ Оголошення надіслано!\n"
        f"📨 Успішно: {success} | ❌ Невдало: {failed}",
        reply_markup=admin_panel_kb(status),
    )
    await state.clear()


# ── Скинути дані ────────────────────────────────────────────

@router.callback_query(F.data == "admin_reset")
async def admin_reset_confirm(callback: CallbackQuery, bot: Bot):
    """Підтвердження скидання даних."""
    if not storage.is_admin(callback.from_user.id):
        await callback.answer("❌ Ти не адмін!", show_alert=True)
        return

    await edit_current(
        bot,
        callback.message.chat.id,
        "🗑️ <b>Скинути ВСІ дані?</b>\n\n"
        "⚠️ Це видалить всі команди, гравців та стан гри!\n"
        "Цю дію не можна скасувати!",
        reply_markup=confirm_kb("reset"),
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_reset")
async def admin_reset(callback: CallbackQuery, bot: Bot):
    """Скидання всіх даних."""
    if not storage.is_admin(callback.from_user.id):
        await callback.answer("❌ Ти не адмін!", show_alert=True)
        return

    storage.reset_all()

    status = storage.get_game_status()
    await edit_current(
        bot,
        callback.message.chat.id,
        "✅ <b>Всі дані скинуто!</b>\n\nМожна починати нову гру.",
        reply_markup=admin_panel_kb(status),
    )
    await callback.answer()


# ── Скасування дій ──────────────────────────────────────────

@router.callback_query(F.data == "cancel_action")
async def cancel_action(callback: CallbackQuery, bot: Bot):
    """Скасувати поточну дію."""
    status = storage.get_game_status()
    await edit_current(
        bot,
        callback.message.chat.id,
        "⚙️ <b>Адмін-панель</b>\n\nОбери дію:",
        reply_markup=admin_panel_kb(status),
    )
    await callback.answer()
