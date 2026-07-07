import random
from pydantic import BaseModel, Field
from .models import GameStage, Role, Player, PlayerType, Team, Message, Action, ActionType, GameEvent, ChannelType
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

    def make_text(self, player) -> str:
        channel_messages = [m for m in self.messages if m.channel in player.role.channels]
        text_list = []

        for m in channel_messages:
             text_list.append(f"[{m.stage} {m.day_number}] {m.player.player_number}: {m.text}")
        return "\n".join(text_list)

    def _get_raw_answer(self, player) -> str:
        if player.player_type == PlayerType.AI:
            return get_ai_answer(prompt=self.make_text(player), system_prompt=player.system_prompt)
        return get_human_answer()

    def _get_player(self, player_number) -> Player:
        for p in self.players:
            if p.player_number == player_number:
                return p

    def get_players_in_night_channel(self, channel: ChannelType) -> list[Player]:
        return [
            p for p in self.alive_players
            if channel in p.role.night_channels and p.role.night_action is not None
        ]

    def get_active_night_channels(self) -> dict[ChannelType, list[Player]]:
        channels: dict[ChannelType, list[Player]] = {}
        for player in self.alive_players:
            if player.role.night_action is None:
                continue
            channel = player.role.night_channel
            if channel is None:
                continue
            channels.setdefault(channel, []).append(player)
        return channels

    def get_player_answer(self, player: Player, channel: ChannelType) -> Message:
        content = self._get_raw_answer(player)
        return Message(
            text=content,
            stage=self.stage,
            player=player,
            day_number=self.day_number,
            channel=channel)

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


    def execute_game_events(self) -> None:
        if self.stage == GameStage.DAY:
            for event in self.current_game_events:
                event.target.is_alive = False
        else:
            heals = [ge.target for ge in self.current_game_events if ge.action_type==ActionType.HEAL]
            target_kills = [ge.target for ge in self.current_game_events if ge.action_type==ActionType.KILL and ge.target not in heals]
            checks = [ge.target for ge in self. current_game_events if ge.action_type==ActionType.ROLE_CHECK]
            for t in target_kills:
                t.is_alive = False
            for c in checks:




    def resolve_day_vote(self) -> None:
        abstain_count = sum(1 for a in self.current_actions if a.target is None)
        votes = Counter(a.target.player_number for a in self.current_actions if a.target is not None)

        if not votes:
            return  # все воздержались

        top_count = max(votes.values())

        if abstain_count >= top_count:
            return  # воздержание побеждает — никого не линчуют

        top_numbers = [number for number, count in votes.items() if count == top_count]

        for number in top_numbers:
            target_player = self._get_player(number)
            self.game_events.append(GameEvent(
                action_type=ActionType.VOTE,
                stage=self.stage,
                day_number=self.day_number,
                target=target_player,
            ))

    def process_day(self) -> None:
        for p in self.alive_players:
            self.messages.append(self.get_player_answer(player=p, channel=ChannelType.DAY))

        for p in self.alive_players:
            self.actions.append(self.get_player_action(action_type=ActionType.VOTE, player=p))

        self.resolve_day_vote()
        self.execute_game_events()


    def _process_night_channel(self, channel: ChannelType, players: list[Player]) -> None:
        # 1. Дискуссия — только если в канале > 1 игрока
        if len(players) > 1:
            for player in players:
                message = self.get_player_answer(player, channel=channel)
                self.messages.append(message)

        for player in players:
            action_type = player.role.night_action
            action = self.get_player_action(action_type, player)
            self.actions.append(action)


    def resolve_night_actions(self) -> None:
        if self.current_actions:
            mafia_votes = Counter(a.target.player_number for a in self.current_actions if a.player.role.team == Team.MAFIA and a.action_type==ActionType.KILL and a.target is not None)
            top_votes = mafia_votes.most_common()
            if top_votes:
                if len(top_votes) > 1 and top_votes[0][1] == top_votes[1][1]:
                    return  # ничья — никто не убит (опционально)
                kill_target = top_votes[0][0]
                self.game_events.append(GameEvent(target=self._get_player(kill_target), stage=self.stage, day_number=self.day_number, action_type=ActionType.KILL))

            not_mafia_actions = [a for a in self.current_actions if a.player.role.team!=Team.MAFIA and a.target is not None]
            for a in not_mafia_actions:
                self.game_events.append(GameEvent(action_type=a.action_type, target=a.target, stage=a.stage, day_number=a.day_number))

    def process_night(self):
        for channel, players in self.get_active_night_channels().items():
            self._process_night_channel(channel, players)

        self.resolve_night_actions()
        self.execute_game_events()





        # for p in [p for p in self.alive_players if p.role.night_action is not None]:
        #     self.actions.append(self.get_player_action(action_type=p.role.night_action, player=p))


