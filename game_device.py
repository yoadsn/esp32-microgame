class GameDisplay:
    def show(self):
        pass

    def fill(self, col):
        pass

    def text(self, string, x, y, col=1):
        pass

    def line(self, start_pos_x, start_pos_y, end_pos_x, end_pos_y, col):
        pass

    def fill_rect(self, x, y, w, h, col):
        pass

    def pixel(self, x, y, col):
        pass


class GameTime:
    def sleep_ms(self, ms):
        pass

    def ticks_ms(self):
        pass

    def ticks_diff(self, a, b):
        pass

    def tick(self, fps):
        pass


class GameButton:
    def __init__(self) -> None:
        pass

    def value(self):
        pass


class GameDevice:
    def __init__(
        self, time: GameTime, display: GameDisplay, button: GameButton
    ) -> None:
        self.time = time
        self.display = display
        self.button = button
