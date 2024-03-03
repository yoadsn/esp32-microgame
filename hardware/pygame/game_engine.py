import pygame
from sys import exit
from typing import Type
from game_device import GameDevice, GameDisplay, GameTime, GameButton
from game_logic import GameLogic


class MockGameDisplay(GameDisplay):
    def __init__(self, width: int = 128, height: int = 64, scale: int = 5):
        self.scale = scale
        self.width = width
        self.height = height
        pygame.font.init()
        self.font = pygame.font.Font(
            "./hardware/pygame/assets/Px437_IBM_EGA_8x8.ttf", 8
        )
        self.last_surface_text = None
        self.screen = pygame.display.set_mode([width * scale, height * scale])
        self.buffer = pygame.Surface([width, height])
        self.colors = [(0, 0, 0), (255, 255, 255)]
        pygame.display.set_caption("Game Engine")

    def show(self):
        scaled = pygame.transform.scale(
            self.buffer, (self.width * self.scale, self.height * self.scale)
        )
        self.screen.blit(scaled, (0, 0))
        pygame.display.flip()

    def fill(self, col):
        self.buffer.fill(self.colors[col])

    def text(self, string, x, y, col=1):
        if self.last_surface_text != string:
            self.last_surface_text = string
            self.last_text_surface = self.font.render(string, False, self.colors[col])
        self.buffer.blit(self.last_text_surface, [x, y])

    def line(self, start_pos_x, start_pos_y, end_pos_x, end_pos_y, col):
        pygame.draw.line(
            self.buffer,
            self.colors[col],
            [start_pos_x, start_pos_y],
            [end_pos_x, end_pos_y],
            1,
        )

    def rect(self, x, y, w, h, col):
        pygame.draw.rect(self.buffer, self.colors[col], [x, y, w, h], 1)

    def fill_rect(self, x, y, w, h, col):
        pygame.draw.rect(self.buffer, self.colors[col], [x, y, w, h])

    def pixel(self, x, y, col):
        if 0 <= x < self.width and 0 <= y < self.height:
            pygame.draw.rect(self.buffer, self.colors[col], [x, y, 1, 1])


class MockTime(GameTime):
    def __init__(self) -> None:
        self.clock = pygame.time.Clock()

    def sleep_ms(self, ms):
        pygame.time.wait(ms)

    def ticks_ms(self):
        return pygame.time.get_ticks()

    def ticks_diff(self, a, b):
        return a - b

    def tick(self, fps):
        self.clock.tick(fps)

    def get_fps(self):
        return self.clock.get_fps()


class MockButton(GameButton):
    def __init__(self) -> None:
        self._value = 1

    def set_value(self, value):
        self._value = value

    def value(self):
        return self._value


class GameEngine:
    def __init__(self) -> None:
        pygame.init()
        self.display = MockGameDisplay(128, 64, 5)
        self.time = MockTime()
        self.button = MockButton()
        self.device = GameDevice(self.time, self.display, self.button)

    def load(self, logic_gen: Type[GameLogic]):
        self.logic = logic_gen(self.device)
        self.logic.load()

    def run(self):
        self.running = True

        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        self.button.set_value(0)
                if event.type == pygame.KEYUP:
                    if event.key == pygame.K_SPACE:
                        self.button.set_value(1)

            self.time.tick(30)

            self.logic.game_tick()

        pygame.quit()
        exit()
