pause = (0, 0, 1)
INTRO_MELODY = [
    (4, 2, 1),
    pause,
    (4, 5, 2),
    #
    (4, 2, 1),
    pause,
    (4, 2, 1),
    (4, 7, 1),
    #
    (4, 2, 1),
    (4, 7, 1),
    (4, 5, 2),
    #
    (4, 7, 1),
    pause,
    (4, 7, 1),
    pause,
    #
    (4, 7, 2),
    (4, 5, 1),
    pause,
    #
    (4, 7, 1),
    (4, 2, 1),
    (4, 5, 1),
    pause,
    #
    (4, 7, 1),
    pause,
    (4, 5, 1),
    (4, 7, 1),
    #
    (4, 2, 1),
    pause,
    (4, 2, 1),
    pause,
]
SHOOT_MELODY = [(6, 1, 1), (5, 1, 2)]
HIT_MELODY = [(3, 6, 1), (3, 5, 1)]
HIT_OTHER_MELODY = [(3, 5, 1), (3, 6, 1)]
CAPTURE_UFO_MELODY = [(6, 4, 1), (6, 5, 1), (6, 6, 1)]


class Sound:
    def __init__(self, audio, sound, interruptable=True) -> None:
        self.audio = audio
        self.sound = sound
        self.interruptable = interruptable

    def play(self):
        self.audio.play(self.sound, self.interruptable)
