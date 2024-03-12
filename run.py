from hardware.esp32.game_engine import GameEngine

Game = __import__("games.mock_game", globals(), locals(), ["GameLogic"])

if __name__ == "__main__":
    print("Game Running__")
    engine = GameEngine()
    engine.load(Game.GameLogic)
    engine.run()
