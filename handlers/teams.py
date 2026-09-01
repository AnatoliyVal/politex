from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from storage import storage
from keyboards.inline import (
    main_menu_kb,
    teams_list_kb,
    team_info_kb,
)
from config import MAX_TEAM_SIZE
from utils.message_manager import send_or_edit, edit_current, delete_user_message

router = Router()


class TeamCreation(StatesGroup):
    """FSM стани для створення команди."""
    waiting_for_name = State()


# ── Створення команди ───────────────────────────────────────

@router.callback_query(F.data == "create_team")
async def create_team_start(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Початок створення команди."""
    # Тільки адміни можуть створювати команди
    if not storage.is_admin(callback.from_user.id):
        await callback.answer("❌ Тільки адміністратор може створювати команди!", show_alert=True)
        return

    if storage.get_game_status() != "registration":
        await callback.answer("❌ Зараз не можна створювати команди. Гра вже йде!", show_alert=True)
        return

    await edit_current(
        bot,
        callback.message.chat.id,
        "🏗️ <b>Створення команди</b>\n\n"
        "Введи назву для своєї команди:",
    )
    await state.set_state(TeamCreation.waiting_for_name)
    await callback.answer()


@router.message(TeamCreation.waiting_for_name)
async def create_team_finish(message: Message, state: FSMContext, bot: Bot):
    """Завершення створення команди."""
    name = message.text.strip()

    # Видаляємо повідомлення користувача
    await delete_user_message(bot, message.chat.id, message.message_id)

    if len(name) < 2:
        await send_or_edit(bot, message.chat.id, "❌ Назва занадто коротка. Введи іншу назву:")
        return

    if len(name) > 30:
        await send_or_edit(bot, message.chat.id, "❌ Назва занадто довга (макс. 30 символів). Введи іншу:")
        return

    # Перевірка чи є вже команда з такою назвою
    for team in storage.get_all_teams().values():
        if team["name"].lower() == name.lower():
            await send_or_edit(bot, message.chat.id, "❌ Команда з такою назвою вже існує. Обери іншу:")
            return

    team_id = storage.create_team(name=name, captain_id=message.from_user.id)

    await send_or_edit(
        bot,
        message.chat.id,
        f"✅ <b>Команду «{name}» створено!</b>\n\n"
        f"👥 Учасники: 0/{MAX_TEAM_SIZE}\n\n"
        f"🔑 Код команди: <code>{team_id}</code>\n"
        f"Надішли цей код гравцям, щоб вони могли приєднатися!",
        reply_markup=main_menu_kb(),
    )
    await state.clear()


# ── Приєднання до команди ───────────────────────────────────

@router.callback_query(F.data == "join_team")
async def show_teams_list(callback: CallbackQuery, bot: Bot):
    """Показати список доступних команд."""
    if storage.get_game_status() != "registration":
        await callback.answer(
            "🔒 Гра вже розпочалась. Ти не можеш змінювати команди зараз.",
            show_alert=True,
        )
        return

    player = storage.get_player(callback.from_user.id)
    if player and player["team_id"]:
        await callback.answer("❌ Ти вже в команді! Спочатку вийди з неї.", show_alert=True)
        return

    teams = storage.get_available_teams()
    await edit_current(
        bot,
        callback.message.chat.id,
        "👥 <b>Доступні команди</b>\n\nОбери команду для приєднання:",
        reply_markup=teams_list_kb(teams),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("join_"))
async def join_team(callback: CallbackQuery, bot: Bot):
    """Приєднатися до обраної команди."""
    team_id = callback.data.replace("join_", "")

    if team_id == "team":
        return

    # Додаткова перевірка: стан гри може змінитись до обробки callback
    if storage.get_game_status() != "registration":
        await callback.answer(
            "🔒 Гра вже розпочалась. Ти не можеш змінювати команди зараз.",
            show_alert=True,
        )
        return

    success, msg = storage.join_team(team_id, callback.from_user.id)

    if success:
        team = storage.get_team(team_id)
        members_count = len(team["members"])
        text = (
            f"{msg}\n\n"
            f"👥 Учасників: {members_count}/{MAX_TEAM_SIZE}"
        )
        await edit_current(bot, callback.message.chat.id, text, reply_markup=main_menu_kb())
    else:
        await callback.answer(msg, show_alert=True)

    await callback.answer()


@router.callback_query(F.data == "no_teams")
async def no_teams_handler(callback: CallbackQuery):
    """Обробка натискання на 'Немає команд'."""
    await callback.answer("Поки що немає доступних команд. Створи свою! 🏗️", show_alert=True)


# ── Моя команда ────────────────────────────────────────────

@router.callback_query(F.data == "my_team")
async def show_my_team(callback: CallbackQuery, bot: Bot):
    """Показати інформацію про свою команду."""
    user_id = callback.from_user.id
    team_id, team = storage.get_player_team(user_id)

    if not team:
        await callback.answer("❌ Ти ще не в жодній команді.", show_alert=True)
        return

    game_active = storage.get_game_status() != "registration"
    is_captain = team["captain_id"] == user_id
    members_info = []
    kick_members = []

    for member_id in team["members"]:
        player = storage.get_player(member_id)
        name = player["full_name"] if player else "Невідомий"
        if member_id == team["captain_id"]:
            members_info.append(f"  👑 {name} (капітан)")
        else:
            members_info.append(f"  👤 {name}")
            if not game_active:
                kick_members.append((member_id, name))

    members_text = "\n".join(members_info)
    members_count = len(team["members"])

    text = (
        f"📋 <b>Команда «{team['name']}»</b>\n\n"
        f"👥 Учасники ({members_count}/{MAX_TEAM_SIZE}):\n"
        f"{members_text}\n\n"
        f"🔑 Код команди: <code>{team_id}</code>"
    )
    if game_active:
        text += "\n\n🔒 <i>Гра активна — зміни заблоковано.</i>"

    await edit_current(
        bot,
        callback.message.chat.id,
        text,
        reply_markup=team_info_kb(team_id, is_captain, kick_members, game_active=game_active),
    )
    await callback.answer()


# ── Вийти з команди ─────────────────────────────────────

@router.callback_query(F.data == "leave_team")
async def leave_team(callback: CallbackQuery, bot: Bot):
    """Вийти з команди."""
    if storage.get_game_status() != "registration":
        await callback.answer(
            "🔒 Гра вже розпочалась. Ти не можеш змінювати команди зараз.",
            show_alert=True,
        )
        return
    success, msg = storage.leave_team(callback.from_user.id)
    await edit_current(bot, callback.message.chat.id, msg, reply_markup=main_menu_kb())
    await callback.answer()


# ── Кікнути учасника ────────────────────────────────────────

@router.callback_query(F.data.startswith("kick_"))
async def kick_member(callback: CallbackQuery, bot: Bot):
    """Капітан кікає учасника."""
    if storage.get_game_status() != "registration":
        await callback.answer(
            "🔒 Гра вже розпочалась. Ти не можеш вигнати учасників зараз.",
            show_alert=True,
        )
        return

    parts = callback.data.split("_")
    # kick_teamid_memberid
    if len(parts) < 3:
        await callback.answer("❌ Помилка", show_alert=True)
        return

    team_id = parts[1]
    target_id = int(parts[2])
    success, msg = storage.kick_member(callback.from_user.id, target_id)

    if success:
        # Оновлюємо вигляд команди
        await show_my_team(callback, bot)
    else:
        await callback.answer(msg, show_alert=True)


@router.callback_query(F.data == "game_active_lock")
async def game_active_lock_handler(callback: CallbackQuery):
    """Заблокована дія: гра вже розпочалась."""
    await callback.answer(
        "🔒 Гра вже розпочалась. Ти не можеш змінювати команди зараз.",
        show_alert=True,
    )
