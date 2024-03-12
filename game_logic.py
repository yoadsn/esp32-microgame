from game_device import GameDevice


class BaseGameLogic:
    def __init__(self, device: GameDevice) -> None:
        self.device = device

    def load(self):
        pass

    def game_tick(self):
        pass
