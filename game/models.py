import enum
from pydantic import BaseModel

class Team(enum.StrEnum):
    MAFIA = "mafia"
    CITIZENS = "citizens"
    NEUTRAL = "neutral"


class PlayerType(enum.StrEnum):
    AI = "ai"
    HUMAN = "human"

class ActionType(enum.StrEnum):
    VOTE = "vote"
    KILL = "kill"
    ROLE_CHECK = "role_check"
    HEAL = "heal"

class ChannelType(enum.StrEnum):
    DAY = "day"
    MAFIA_NIGHT = "mafia_night"
    PRIVATE = "private"


class Role(enum.StrEnum):
    MAFIA = "mafia"
    CITIZEN = "citizen"
    DOCTOR = "doctor"
    SHERIFF = "sheriff"

    @property
    def team(self) -> Team:
        mapping = {
            Role.MAFIA: Team.MAFIA,
            Role.CITIZEN: Team.CITIZENS,
            Role.DOCTOR: Team.CITIZENS,
            Role.SHERIFF: Team.CITIZENS
        }
        return mapping[self]

    @property
    def night_action(self) -> ActionType | None:
        mapping = {
            Role.MAFIA: ActionType.KILL,
            Role.CITIZEN: None,
            Role.SHERIFF: ActionType.ROLE_CHECK,
            Role.DOCTOR: ActionType.HEAL
        }
        return mapping[self]

    @property
    def channels(self) -> list[ChannelType]:
        mapping = {
            Role.MAFIA: [ChannelType.DAY, ChannelType.MAFIA_NIGHT],
            Role.CITIZEN: [ChannelType.DAY],
            Role.DOCTOR: [ChannelType.DAY, ChannelType.PRIVATE],
            Role.SHERIFF: [ChannelType.DAY, ChannelType.PRIVATE]
        }
        return mapping[self]

    @property
    def night_channels(self) -> list[ChannelType]:
        return [c for c in self.channels if c!= ChannelType.DAY]

    @property
    def night_channel(self) -> ChannelType | None:
        """Один канал, где игрок действует ночью (для группировки)."""
        channels = self.night_channels
        return channels[0] if channels else None

class Player(BaseModel):
    role: Role
    player_type: PlayerType
    player_number: int
    is_alive: bool = True
    system_prompt: str | None = None

class GameStage(enum.StrEnum):
    DAY = "day"
    NIGHT = "night"




class Message(BaseModel):
    channel: ChannelType
    text: str
    player: Player | None = None  # Кто отправил (None для системы)
    recipient: Player | None = None  # Кому адресовано (для приватных шепотов)
    stage: GameStage
    day_number: int




class Action(BaseModel):
    action_type: ActionType
    stage: GameStage
    day_number: int
    player: Player
    target: Player | None = None


class GameEvent(BaseModel):
    action_type: ActionType
    stage: GameStage
    day_number: int
    target: Player
    player: Player | None = None  # <--- Инициатор события (кто совершил действие)