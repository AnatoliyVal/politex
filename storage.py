import json
import os
import uuid
from datetime import datetime
from config import DATA_FILE, MAX_TEAM_SIZE


class Storage:
    """Менеджер JSON сховища для даних гри."""

    def __init__(self):
        self.data = self._load()

    def _load(self) -> dict:
        """Завантажити дані з JSON файлу."""
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return self._default_data()

    def _default_data(self) -> dict:
        """Початкова структура даних."""
        return {
            "teams": {},
            "players": {},
            "admins": [],
            "game": {
                "status": "registration",  # registration | active | finished
                "started_at": None,
                "timer_end": None,
            },
            "bot_messages": {},  # {user_id: [message_id, ...]}
        }

    def save(self):
        """Зберегти дані в JSON файл."""
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    # ── Гравці ──────────────────────────────────────────────

    def add_player(self, user_id: int, username: str, full_name: str):
        """Зареєструвати гравця."""
        uid = str(user_id)
        if uid not in self.data["players"]:
            self.data["players"][uid] = {
                "username": username,
                "full_name": full_name,
                "team_id": None,
                "registered_at": datetime.now().isoformat(),
            }
            self.save()

    def get_player(self, user_id: int) -> dict | None:
        """Отримати дані гравця."""
        return self.data["players"].get(str(user_id))

    def is_registered(self, user_id: int) -> bool:
        """Чи зареєстрований гравець."""
        return str(user_id) in self.data["players"]

    def get_all_player_ids(self) -> list[int]:
        """Отримати ID всіх зареєстрованих гравців."""
        return [int(uid) for uid in self.data["players"]]

    # ── Команди ─────────────────────────────────────────────

    def create_team(self, name: str, captain_id: int) -> str:
        """Створити команду. Повертає team_id."""
        team_id = uuid.uuid4().hex[:8]
        self.data["teams"][team_id] = {
            "name": name,
            "captain_id": captain_id,
            "members": [captain_id],
            "score": 0,
            "created_at": datetime.now().isoformat(),
        }
        # Прив'язати капітана до команди
        self.data["players"][str(captain_id)]["team_id"] = team_id
        self.save()
        return team_id

    def join_team(self, team_id: str, user_id: int) -> tuple[bool, str]:
        """Приєднатися до команди. Повертає (success, message)."""
        team = self.data["teams"].get(team_id)
        if not team:
            return False, "❌ Команду не знайдено."

        if len(team["members"]) >= MAX_TEAM_SIZE:
            return False, f"❌ Команда вже повна ({MAX_TEAM_SIZE}/{MAX_TEAM_SIZE})."

        player = self.get_player(user_id)
        if player and player["team_id"]:
            return False, "❌ Ти вже в іншій команді. Спочатку вийди з неї."

        if user_id in team["members"]:
            return False, "❌ Ти вже в цій команді."

        team["members"].append(user_id)
        self.data["players"][str(user_id)]["team_id"] = team_id
        self.save()
        return True, f"✅ Ти приєднався до команди «{team['name']}»!"

    def leave_team(self, user_id: int) -> tuple[bool, str]:
        """Вийти з команди."""
        player = self.get_player(user_id)
        if not player or not player["team_id"]:
            return False, "❌ Ти не в жодній команді."

        team_id = player["team_id"]
        team = self.data["teams"].get(team_id)
        if not team:
            return False, "❌ Команду не знайдено."

        # Якщо капітан виходить — видаляємо команду
        if team["captain_id"] == user_id:
            # Повертаємо всіх учасників
            for member_id in team["members"]:
                self.data["players"][str(member_id)]["team_id"] = None
            del self.data["teams"][team_id]
            self.save()
            return True, "✅ Ти вийшов з команди. Оскільки ти був капітаном — команду розпущено."

        team["members"].remove(user_id)
        player["team_id"] = None
        self.save()
        return True, "✅ Ти вийшов з команди."

    def kick_member(self, captain_id: int, target_id: int) -> tuple[bool, str]:
        """Капітан кікає учасника."""
        player = self.get_player(captain_id)
        if not player or not player["team_id"]:
            return False, "❌ Ти не в жодній команді."

        team_id = player["team_id"]
        team = self.data["teams"].get(team_id)
        if not team:
            return False, "❌ Команду не знайдено."

        if team["captain_id"] != captain_id:
            return False, "❌ Тільки капітан може кікати учасників."

        if target_id not in team["members"]:
            return False, "❌ Цього гравця немає в команді."

        if target_id == captain_id:
            return False, "❌ Не можна кікнути самого себе."

        team["members"].remove(target_id)
        self.data["players"][str(target_id)]["team_id"] = None
        self.save()
        target_name = self.data["players"][str(target_id)]["full_name"]
        return True, f"✅ Гравця {target_name} вигнано з команди."

    def get_team(self, team_id: str) -> dict | None:
        """Отримати дані команди."""
        return self.data["teams"].get(team_id)

    def get_all_teams(self) -> dict:
        """Отримати всі команди."""
        return self.data["teams"]

    def get_available_teams(self) -> dict:
        """Команди де є вільні місця."""
        return {
            tid: team
            for tid, team in self.data["teams"].items()
            if len(team["members"]) < MAX_TEAM_SIZE
        }

    def get_player_team(self, user_id: int) -> tuple[str | None, dict | None]:
        """Отримати команду гравця. Повертає (team_id, team_data)."""
        player = self.get_player(user_id)
        if not player or not player["team_id"]:
            return None, None
        team_id = player["team_id"]
        return team_id, self.data["teams"].get(team_id)

    # ── Адміни ──────────────────────────────────────────────

    def add_admin(self, user_id: int):
        """Додати адміна."""
        if user_id not in self.data["admins"] and str(user_id) not in self.data["admins"]:
            self.data["admins"].append(user_id)
            self.save()

    def is_admin(self, user_id: int) -> bool:
        """Чи є користувач адміном."""
        return user_id in self.data["admins"] or str(user_id) in [str(a) for a in self.data["admins"]]

    # ── Гра ─────────────────────────────────────────────────

    def get_game_status(self) -> str:
        """Отримати статус гри."""
        return self.data["game"]["status"]

    def get_round(self) -> int:
        """Отримати номер поточного раунду."""
        return self.data["game"].get("round", 0)

    def set_game_status(self, status: str):
        """Змінити статус гри."""
        self.data["game"]["status"] = status
        if status == "active":
            self.data["game"]["started_at"] = datetime.now().isoformat()
            # Збільшуємо номер раунду
            self.data["game"]["round"] = self.data["game"].get("round", 0) + 1
        self.save()

    def set_timer_end(self, timer_end: str):
        """Встановити час закінчення таймера."""
        self.data["game"]["timer_end"] = timer_end
        self.save()

    def reset_all(self):
        """Скинути всі дані гри (зберігаючи список адмінів)."""
        current_admins = self.data.get("admins", [])
        self.data = self._default_data()
        self.data["admins"] = current_admins
        self.save()

    def get_stats(self) -> dict:
        """Статистика гри."""
        teams = self.data["teams"]
        players = self.data["players"]
        return {
            "total_players": len(players),
            "total_teams": len(teams),
            "players_in_teams": sum(1 for p in players.values() if p["team_id"]),
            "players_without_team": sum(
                1 for p in players.values() if not p["team_id"]
            ),
            "game_status": self.data["game"]["status"],
            "round": self.data["game"].get("round", 0),
        }

    # ── ID бот-повідомлень ──────────────────────────────────

    def save_bot_message(self, user_id: int, message_id: int):
        """Запам'ятати ID бот-повідомлення для користувача."""
        uid = str(user_id)
        if "bot_messages" not in self.data:
            self.data["bot_messages"] = {}
        self.data["bot_messages"][uid] = message_id
        self.save()

    def get_bot_message(self, user_id: int) -> int | None:
        """Отримати ID останнього бот-повідомлення для користувача."""
        if "bot_messages" not in self.data:
            return None
        return self.data["bot_messages"].get(str(user_id))

    def clear_bot_message(self, user_id: int):
        """Видалити запис про бот-повідомлення для користувача."""
        if "bot_messages" in self.data:
            self.data["bot_messages"].pop(str(user_id), None)
            self.save()

    # ── Бали та рейтинг ────────────────────────────────────

    def add_score(self, team_id: str, points: int):
        """Додати бали команді."""
        team = self.data["teams"].get(team_id)
        if team:
            team["score"] = team.get("score", 0) + points
            self.save()

    def set_score(self, team_id: str, points: int):
        """Встановити бали команді (для корекції)."""
        team = self.data["teams"].get(team_id)
        if team:
            team["score"] = points
            self.save()

    def get_leaderboard(self) -> list[tuple[str, str, int]]:
        """Отримати рейтинг команд. Повертає [(team_id, name, score), ...] відсортовано."""
        result = []
        for team_id, team in self.data["teams"].items():
            result.append((team_id, team["name"], team.get("score", 0)))
        result.sort(key=lambda x: x[2], reverse=True)
        return result


# Глобальний екземпляр сховища
storage = Storage()
