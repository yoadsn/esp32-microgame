import random
from game_device import GameDevice
from game_logic import BaseGameLogic


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
        if self.x <= 0 or self.x >= width:
            self.vx *= -1
        if self.y <= 0 or self.y >= height:
            self.vy *= -1


class GameLogic(BaseGameLogic):
    def __init__(self, device: GameDevice) -> None:
        self.screen_width = device.display.width
        self.screen_height = device.display.height
        self.last_refresh = 0
        super().__init__(device)

    def load(self):
        print("game loaded")
        self.start_game_tick = self.device.time.ticks_ms()
        ball_sprite = self.device.display.get_buffer(bytearray(
            (0b10100000,
             0b01000000,
             0b10100000)), 3, 3)
        self.ball1 = Ball(ball_sprite, -1, -1)
        self.ball2 = Ball(ball_sprite, -1, -1)
        self.ball3 = Ball(ball_sprite, -1, -1)

    def game_tick(self):
        device = self.device
        display = device.display
        time = device.time
        button = device.button

        display.fill(0)

        self.ball1.move()
        self.ball1.bounce(self.screen_width, self.screen_height)
        self.ball1.draw(display)

        self.ball2.move()
        self.ball2.bounce(self.screen_width, self.screen_height)
        self.ball2.draw(display)

        self.ball3.move()
        self.ball3.bounce(self.screen_width, self.screen_height)
        self.ball3.draw(display)

        display.rect(0, 0, 128, 64, 1)

        display.show()
