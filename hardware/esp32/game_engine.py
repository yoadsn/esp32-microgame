import time
from typing import Type
from game_logic import GameLogic
from machine import Pin, I2C, RTC
import ssd1306

from game_device import GameDevice

i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=4000000)
display = ssd1306.SSD1306_I2C(128, 64, i2c)  # display object
button = Pin(4, Pin.IN, Pin.PULL_UP)


class GameEngine:
    def __init__(self) -> None:
        self.device = GameDevice(time, display, button)

    def load(self, logic_gen: Type[GameLogic]):
        self.logic = logic_gen(self.device)
        self.logic.load()

    def run(self):
        self.running = True

        while self.running:
            self.logic.game_tick()
