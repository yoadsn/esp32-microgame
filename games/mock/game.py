import random
from game_device import GameDevice
from game_logic import BaseGameLogic

pause = (0, 0, 1)
intro_melody = [
    (4, 0, 1),  # C
    pause,  # Short pause
    (4, 0, 1),  # C
    pause,  # Short pause
    (4, 7, 1),  # G
    pause,  # Short pause
    (4, 7, 1),  # G
    pause,  # Short pause
    (4, 9, 1),  # A
    pause,  # Short pause
    (4, 9, 1),  # A
    pause,  # Short pause
    (4, 7, 1),  # G
    pause,  # Short pause
    pause,  # Short pause
    pause,  # Short pause
    (4, 5, 1),  # F
    pause,  # Short pause
    (4, 5, 1),  # F
    pause,  # Short pause
    (4, 4, 1),  # E
    pause,  # Short pause
    (4, 4, 1),  # E
    pause,  # Short pause
    (4, 2, 1),  # D
    pause,  # Short pause
    (4, 2, 1),  # D
    pause,  # Short pause
    (4, 0, 1),  # C
    pause,  # Short pause
    pause,  # Short pause
    pause,  # Short pause
]

ball_sound = [(5, 0, 1), (6, 0, 1)]


class Ball:
    def __init__(self, sprite, sprite_offset_x=0, sprite_offset_y=1):
        self.x = 10  # Initial X position, to be set by game logic
        self.y = 10  # Initial Y position, to be set by game logic
        self.sprite = sprite
        self.sprite_offset_x = sprite_offset_x
        self.sprite_offset_y = sprite_offset_y
        # Velocity attributes to be set by game logic
        self.vx = 1 + int(random.random() * 4)
        self.vy = 1 + int(random.random() * 2)

    def move(self):
        # Move the ball according to its velocity
        self.x += self.vx
        self.y += self.vy

    def draw(self, display):
        display.blit(
            self.sprite, self.x + self.sprite_offset_x, self.y + self.sprite_offset_y
        )

    def bounce(self, width, height):
        # Bounce off the walls by inverting velocity when hitting boundaries
        did_bounce = False
        if self.x <= 0 or self.x >= width:
            self.vx *= -1
            did_bounce = True
        if self.y <= 0 or self.y >= height:
            self.vy *= -1
            did_bounce = True
        return did_bounce


class GameLogic(BaseGameLogic):
    def __init__(self, device: GameDevice) -> None:
        self.screen_width = device.display.width
        self.screen_height = device.display.height
        self.last_refresh = 0
        super().__init__(device)

    def load(self):
        print("game loaded")
        self.intro_melody = self.device.audio.load_melody(intro_melody)
        self.ball_bump = self.device.audio.load_melody(ball_sound)
        self.start_game_tick = self.device.time.ticks_ms()
        ball_sprite = self.device.display.get_buffer(
            bytearray((0b10100000, 0b01000000, 0b10100000)), 3, 3
        )
        self.ball1 = Ball(ball_sprite, -1, -1)
        self.ball2 = Ball(ball_sprite, -1, -1)
        self.ball3 = Ball(ball_sprite, -1, -1)
        self.device.audio.play(self.intro_melody, False)

    def game_tick(self):
        device = self.device
        display = device.display
        time = device.time
        button = device.button

        display.fill(0)

        self.ball1.move()
        did_bounce = self.ball1.bounce(self.screen_width, self.screen_height)
        self.ball1.draw(display)

        self.ball2.move()
        did_bounce = (
            self.ball2.bounce(self.screen_width, self.screen_height) or did_bounce
        )
        self.ball2.draw(display)

        self.ball3.move()
        did_bounce = (
            self.ball3.bounce(self.screen_width, self.screen_height) or did_bounce
        )
        self.ball3.draw(display)

        if did_bounce:
            self.device.audio.play(self.ball_bump)
            pass

        display.rect(0, 0, 128, 64, 1)

        display.show()
