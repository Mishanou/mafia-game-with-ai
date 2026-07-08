from pathlib import Path

from ..models import Player, Team, GameStage, ActionType
from .tasks import TASKS
from .templates import USER_PROMPT
from ..models import ChannelType


SYSTEM_PROMPTS_DIR = Path(__file__).parent / "system"


class PromptBuilder:
    @staticmethod
    def get_system_prompt(player: Player) -> str:
        path = SYSTEM_PROMPTS_DIR / f"{player.role.value}.txt"
        return path.read_text(encoding="utf-8")

    @staticmethod
    def get_user_prompt(game, player: Player, action_type: ActionType | None = None) -> str:
        return USER_PROMPT.format(
            day=game.day_number,
            stage=game.stage.value,
            alive_players=PromptBuilder._alive_players(game),
            history=PromptBuilder._history(game, player),
            private_information=PromptBuilder._private_information(game, player),
            task=PromptBuilder._task(action_type),
        )

    @staticmethod
    def _alive_players(game) -> str:
        return "\n".join(
            f"- Игрок {player.player_number}"
            for player in game.alive_players
        )

    @staticmethod
    def _history(game, player: Player) -> str:
        visible_messages = []

        for message in game.messages:
            if message.channel == ChannelType.PRIVATE and message.recipient == player:
                visible_messages.append(message)
            # 1. Все живые игроки видят дневные сообщения
            elif message.channel != ChannelType.PRIVATE and message.channel in player.role.channels:
                visible_messages.append(message)

        if not visible_messages:
            return "История пока отсутствует."

        # Сортируем историю по дням и стадиям для удобства ИИ
        return "\n".join(
            f"[{message.stage.value.upper()} {message.day_number}] "
            f"{'Система' if message.player is None else f'Игрок {message.player.player_number}'}: {message.text}"
            for message in visible_messages
        )

    @staticmethod
    def _private_information(game, player: Player) -> str:
        if player.role.team != Team.MAFIA:
            return ""

        mafia_members = [
            f"Игрок {other.player_number}"
            for other in game.alive_players
            if other.role.team == Team.MAFIA and other != player
        ]

        if mafia_members:
            return (
                "Твои союзники:\n"
                + "\n".join(f"- {member}" for member in mafia_members)
            )

        return "Ты единственный оставшийся мафиози."

    @staticmethod
    def _task(action_type: ActionType | None) -> str:
        return TASKS.get(action_type, TASKS[None])