import random
from pydantic import BaseModel, Field
from .models import GameStage, Role, Player, PlayerType, Team, Message, Action, ActionType, GameEvent
from player_actions.human_input import get_human_answer
from player_actions.ai_client import get_ai_answer
from collections import Counter


class Game (BaseModel):
    stage: GameStage = GameStage.NIGHT
    day_number: int = 0
    roles: dict[Role, int]
    messages: list[Message] = Field(default_factory=list)
    players: list[Player] = Field(default_factory=list)
    is_active: bool = True
    actions: list[Action] = Field(default_factory=list)
    game_events: list[GameEvent] = Field(default_factory=list)

    @property
    def alive_players(self) -> list[Player]:
        return [p for p in self.players if p.is_alive]

    @property
    def current_actions(self) -> list[Action]:
        return [a for a in self.actions if a.day_number == self.day_number and a.stage == self.stage]

    @property
    def current_game_events(self) -> list[GameEvent]:
        return [ge for ge in self.game_events if ge.day_number == self.day_number and ge.stage == self.stage]

    def distribute_roles_and_types(self) -> None:
        if self.players or not self.roles:
            return
        roles_list = []
        for role, count in self.roles.items():
            for _ in range(count):
                roles_list.append(role)

        human_player_number = random.randint(1, len(roles_list))
        random.shuffle(roles_list)
        for i, role in enumerate(roles_list):
            player_type = PlayerType.HUMAN if i+1==human_player_number else PlayerType.AI
            player = Player(player_number=i+1, role=role, player_type=player_type)
            self.players.append(player)

    def change_stage(self) -> None:
        if self.check_win_cons():
            self.is_active = False
            return

        if self.stage == GameStage.NIGHT:
            self.stage = GameStage.DAY
            self.day_number += 1
        else:
            self.stage = GameStage.NIGHT

    def check_win_cons(self):
        teams = {team: 0 for team in Team}
        alive_players = [player for player in self.players if player.is_alive]
        for player in alive_players:
            teams[player.role.team] += 1

        if not teams[Team.MAFIA] and not teams[Team.NEUTRAL]:
            return Team.CITIZENS
        elif teams[Team.MAFIA] >= teams[Team.CITIZENS] and not teams[Team.NEUTRAL]:
            return Team.MAFIA
        elif teams[Team.NEUTRAL] >= teams[Team.CITIZENS] and not teams[Team.MAFIA]:
            return Team.NEUTRAL
        else:
            return None

    def make_text(self, team) -> str:
        text_list = []
        if team == Team.CITIZENS:
            team_messages = [m for m in self.messages if m.stage == GameStage.DAY]
        else:
            team_messages = self.messages

        for m in team_messages:
             text_list.append(f"[{m.stage} {m.day_number}] {m.player.player_number}: {m.text}")
        return "\n".join(text_list)

    def _get_raw_answer(self, player) -> str:
        if player.player_type == PlayerType.AI:
            return get_ai_answer(prompt=self.make_text(player.role.team), system_prompt=player.system_prompt)
        return get_human_answer()

    def _get_player(self, player_number) -> Player:
        for p in self.players:
            if p.player_number == player_number:
                return p

    def get_player_answer(self, player: Player) -> Message:
        content = self._get_raw_answer(player)
        return Message(text=content, stage=self.stage, player=player, day_number=self.day_number)

    def get_player_action(self, action_type: ActionType, player: Player) -> Action:
        content = self._get_raw_answer(player)
        try:
            target = self._get_player(int(content))
            if target is None:
                raise ValueError
            return Action(stage=self.stage, player=player, day_number=self.day_number, target=target,
                          action_type=action_type)
        except ValueError:
            print("Повторите попытку.")
            return self.get_player_action(action_type, player)

    def get_game_events(self):
        if self.stage == GameStage.DAY:
            votes = Counter([a.target for a in self.current_actions])
            target_player = max(votes, key=votes.get)
            self.game_events.append(GameEvent(action_type=ActionType.VOTE, stage=self.stage, day_number=self.day_number, target=target_player))


    def execute_game_events(self) -> None:
        if self.stage == GameStage.DAY:
            self.current_game_events[0].target.is_alive = False




    def process_day(self) -> None:
        for p in self.alive_players:
            self.messages.append(self.get_player_answer(p))

        for p in self.alive_players:
            self.actions.append(self.get_player_action(action_type=ActionType.VOTE, player=p))

        self.get_game_events()
        self.execute_game_events()


    def process_night(self):
        pass