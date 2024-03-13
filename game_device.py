class GameDisplay:
    def show(self):
        pass

    def fill(self, col):
        pass

    def center_text(self, string, col):
        pass

    def text(self, string, x, y, col=1):
        pass

    def line(self, start_pos_x, start_pos_y, end_pos_x, end_pos_y, col):
        pass

    def fill_rect(self, x, y, w, h, col):
        pass

    def rect(self, x, y, w, h, col):
        pass

    def pixel(self, x, y, col):
        pass

    def get_buffer(self, data_ba, w, h):
        pass

    def blit(self, buf, x, y):
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


class GameSound:
    def __init__(self) -> None:
        pass


class GameAudio:
    def __init__(self) -> None:
        pass

    def play(self, sound_id, interruptable):
        pass

    def load_melody(self, melody):
        pass

    def note_to_freq(self, octave: int, note_idx: int) -> int:
        if octave == 0:
            return 0
        # Distance of C from A in the equal-tempered scale
        distance_from_a = note_idx - 9

        # Adjusting for the octave
        n = (octave - 4) * 12 + distance_from_a

        # Calculate the frequency
        freq = 440 * (2 ** (n / 12))

        # Return the frequency rounded to the nearest whole number
        return round(freq)


class GameDevice:
    def __init__(
        self, time: GameTime, display: GameDisplay, button: GameButton, audio: GameAudio
    ) -> None:
        self.time = time
        self.display = display
        self.button = button
        self.audio = audio
