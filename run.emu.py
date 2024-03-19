from hardware.pygame.game_engine import GameEngine

Game = __import__("games.duel.game", globals(), locals(), ["GameLogic"])

if __name__ == "__main__":
    engine = GameEngine()
    engine.load(Game.GameLogic)
    engine.run()
