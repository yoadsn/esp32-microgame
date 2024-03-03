from hardware.pygame.game_engine import GameEngine
#from hardware.esp32.game_engine import GameEngine
from games.morse_game import MorseGameLogic

if __name__ == "__main__":
    engine = GameEngine()
    engine.load(MorseGameLogic)
    engine.run()
