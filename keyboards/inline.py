from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import MAX_TEAM_SIZE


def main_menu_kb() -> InlineKeyboardMarkup:
    """Головне меню."""
    buttons = [
        [
            InlineKeyboardButton(
                text="👥 Приєднатися до команди", callback_data="join_team"
            )
        ],
        [
            InlineKeyboardButton(
                text="📋 Моя команда", callback_data="my_team"
            )
        ],
        [
            InlineKeyboardButton(
                text="🏆 Рейтинг команд", callback_data="leaderboard"
            )
        ],
        [
            InlineKeyboardButton(
                text="ℹ️ Правила гри", callback_data="rules"
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def teams_list_kb(teams: dict) -> InlineKeyboardMarkup:
    """Список команд для приєднання."""
    buttons = []
    for team_id, team in teams.items():
        members_count = len(team["members"])
        text = f"👥 {team['name']} ({members_count}/{MAX_TEAM_SIZE})"
        buttons.append(
            [InlineKeyboardButton(text=text, callback_data=f"join_{team_id}")]
        )

    if not buttons:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="😔 Немає доступних команд", callback_data="no_teams"
                )
            ]
        )

    buttons.append(
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_menu")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def team_info_kb(
    team_id: str,
    is_captain: bool,
    members: list,
    game_active: bool = False,
) -> InlineKeyboardMarkup:
    """Інфо про команду з діями."""
    buttons = []

    if not game_active:
        if is_captain:
            # Кнопки для кікання кожного учасника (крім капітана)
            for member_id, member_name in members:
                buttons.append(
                    [
                        InlineKeyboardButton(
                            text=f"❌ Вигнати {member_name}",
                            callback_data=f"kick_{team_id}_{member_id}",
                        )
                    ]
                )

        buttons.append(
            [
                InlineKeyboardButton(
                    text="🚶 Вийти з команди", callback_data="leave_team"
                )
            ]
        )
    else:
        # Гра активна — заборонено змінювати команду
        buttons.append(
            [
                InlineKeyboardButton(
                    text="🔒 Гра вже розпочалась", callback_data="game_active_lock"
                )
            ]
        )

    buttons.append(
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_menu")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_teams_kb(teams: dict) -> InlineKeyboardMarkup:
    """Список команд для адміна (з кнопкою Delete)."""
    buttons = []
    for team_id, team in teams.items():
        members_count = len(team["members"])
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"🏷️ {team['name']} ({members_count}/{MAX_TEAM_SIZE})",
                    callback_data="noop",
                ),
                InlineKeyboardButton(
                    text="🗑️ Видалити",
                    callback_data=f"admin_delete_team_{team_id}",
                ),
            ]
        )
    buttons.append(
        [InlineKeyboardButton(text="🔙 Адмін-панель", callback_data="admin_panel")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_panel_kb(game_status: str) -> InlineKeyboardMarkup:
    """Панель адміністратора."""
    buttons = [
        [
            InlineKeyboardButton(
                text="📊 Статус гри", callback_data="admin_status"
            )
        ],
        [
            InlineKeyboardButton(
                text="👥 Список команд", callback_data="admin_teams"
            )
        ],
        [
            InlineKeyboardButton(
                text="🏆 Рейтинг", callback_data="leaderboard"
            )
        ],
    ]

    if game_status == "registration":
        buttons.append(
            [
                InlineKeyboardButton(
                    text="🏗️ Додати команду", callback_data="create_team"
                )
            ]
        )
        buttons.append(
            [
                InlineKeyboardButton(
                    text="🚀 Почати гру", callback_data="admin_start_game"
                )
            ]
        )
    elif game_status == "active":
        buttons.append(
            [
                InlineKeyboardButton(
                    text="⏹️ Завершити раунд", callback_data="admin_stop_game"
                ),
                InlineKeyboardButton(
                    text="▶️ Наступний раунд", callback_data="admin_next_round"
                ),
            ]
        )
        buttons.append(
            [
                InlineKeyboardButton(
                    text="⭐ Виставити бали", callback_data="admin_set_scores"
                )
            ]
        )
        buttons.append(
            [
                InlineKeyboardButton(
                    text="🏁 Завершити гру (Фінал)", callback_data="admin_finish_game"
                )
            ]
        )
    elif game_status == "finished":
        buttons.append(
            [
                InlineKeyboardButton(
                    text="⭐ Виставити бали", callback_data="admin_set_scores"
                )
            ]
        )
        buttons.append(
            [
                InlineKeyboardButton(
                    text="▶️ Наступний раунд", callback_data="admin_next_round"
                )
            ]
        )
        buttons.append(
            [
                InlineKeyboardButton(
                    text="🏁 Завершити гру (Фінал)", callback_data="admin_finish_game"
                )
            ]
        )
    elif game_status == "game_over":
        buttons.append(
            [
                InlineKeyboardButton(
                    text="⭐ Коригувати бали", callback_data="admin_set_scores"
                )
            ]
        )
        buttons.append(
            [
                InlineKeyboardButton(
                    text="📢 Надіслати результати ще раз", callback_data="admin_finish_game"
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="🔔 Надіслати оголошення", callback_data="admin_announce"
            )
        ]
    )
    buttons.append(
        [
            InlineKeyboardButton(
                text="🗑️ Скинути всі дані", callback_data="admin_reset"
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_kb(action: str) -> InlineKeyboardMarkup:
    """Клавіатура підтвердження дій."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Підтвердити", callback_data=f"confirm_{action}"
                ),
                InlineKeyboardButton(
                    text="❌ Скасувати", callback_data="cancel_action"
                ),
            ]
        ]
    )


def back_to_admin_kb() -> InlineKeyboardMarkup:
    """Кнопка повернення до адмін-панелі."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔙 Адмін-панель", callback_data="admin_panel"
                )
            ]
        ]
    )


def score_teams_kb(teams: dict) -> InlineKeyboardMarkup:
    """Клавіатура для вибору команди для нарахування балів."""
    buttons = []
    for team_id, team in teams.items():
        score = team.get("score", 0)
        text = f"⭐ {team['name']} (бали: {score})"
        buttons.append(
            [InlineKeyboardButton(text=text, callback_data=f"score_{team_id}")]
        )

    buttons.append(
        [InlineKeyboardButton(text="🔙 Адмін-панель", callback_data="admin_panel")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)
