from .core import Game
from .models import Role, GameStage


if __name__ == '__main__':
    game = Game(roles = {Role.MAFIA: 1, Role.CITIZEN: 2})
    game.distribute_roles_and_types()
    while game.is_active:
        game.process_night() if game.stage == GameStage.NIGHT else game.process_day()
        game.change_stage()





