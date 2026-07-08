# Если файлы лежат в одной папке, импортируем без точек:
from game.core import Game
from game.models import Role, GameStage

if __name__ == '__main__':
    game = Game(roles={
        Role.MAFIA: 2,
        Role.SHERIFF: 1,
        Role.DOCTOR: 1,
        Role.CITIZEN: 3
    })

    game.distribute_roles_and_types()

    while game.is_active:
        if game.stage == GameStage.NIGHT:
            # Перед ночью можно сделать паузу, чтобы текст читался удобнее
            input("\nНажмите Enter, чтобы наступила ночь...")
            game.process_night()
        else:
            game.process_day()

        game.change_stage()

    # Конец игры
    winner_team = game.check_win_cons()
    print("\n==========================================")
    print(f"🎉 ИГРА ОКОНЧЕНА! Победила команда: {winner_team.value.upper()}")
    print("==========================================")