import pygame
from sys import exit
from typing import Type
from game_device import GameDevice, GameDisplay, GameTime, GameButton
from game_logic import BaseGameLogic


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
        self.inv_mask = pygame.Surface([width, height])
        self.inverted = False
        pygame.display.set_caption("Game Engine")

    def invert(self, is_on):
        self.inverted = is_on == 1

    def show(self):
        to_apply = self.buffer
        if self.inverted:
            self.inv_mask.fill(self.colors[1])
            self.inv_mask.blit(self.buffer, (0, 0), None, pygame.BLEND_SUB)
            to_apply = self.inv_mask
        scaled = pygame.transform.scale(
            to_apply, (self.width * self.scale, self.height * self.scale)
        )
        self.screen.blit(scaled, (0, 0))

        pygame.display.flip()

    def fill(self, col):
        self.buffer.fill(self.colors[col])

    def text(self, string, x, y, col=1):
        if self.last_surface_text != string:
            self.last_surface_text = string
            self.last_text_surface = self.font.render(string, False, self.colors[col])
        self.buffer.blit(self.last_text_surface, [x, y], None)

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

    def get_buffer(self, data_ba, w, h):
        surface_buffer = pygame.Surface((w, h))
        bytes_w = ((w - 1) // 8) + 1
        for y in range(0, h):
            for x in range(0, w):
                by = y * bytes_w + x // 8
                bi = x % 8
                val = (data_ba[by] >> (7 - bi)) & 0x01
                pygame.draw.rect(surface_buffer, self.colors[val], [x, y, 1, 1])

        return surface_buffer

    def blit(self, buf, x, y):
        self.buffer.blit(buf, [x, y])


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
        self.display = MockGameDisplay(128, 64, 3)
        self.time = MockTime()
        self.button = MockButton()
        self.device = GameDevice(self.time, self.display, self.button)

    def load(self, logic_gen: Type[BaseGameLogic]):
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
                    elif event.key == pygame.K_ESCAPE:
                        self.running = False
                if event.type == pygame.KEYUP:
                    if event.key == pygame.K_SPACE:
                        self.button.set_value(1)

            self.time.tick(30)

            self.logic.game_tick()

        pygame.quit()
        exit()
