from hardware.esp32.game_engine import GameEngine

Game = __import__("games.duel.game", globals(), locals(), ["GameLogic"])

if __name__ == "__main__":
    print("Game Running")
    engine = GameEngine()
    engine.load(Game.GameLogic)
    engine.run()
