import time
from machine import Pin, SoftI2C
from hardware.esp32 import ssd1306

from game_device import GameDevice

i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=4000000)
display = ssd1306.SSD1306_I2C(128, 64, i2c)  # display object
button = Pin(4, Pin.IN, Pin.PULL_UP)
target_fps = 24
target_tick_length_us = 1_000_000 // target_fps


class GameEngine:
    def __init__(self) -> None:
        self.device = GameDevice(time, display, button)

    def load(self, logic_gen):
        self.logic = logic_gen(self.device)
        self.logic.load()

    def run(self):
        self.running = True
        device_time = self.device.time

        elapsed_time_anchor_us = device_time.ticks_us()
        elapsed_frame_count = 0
        while self.running:
            tick_start_us = device_time.ticks_us()
            self.logic.game_tick()
            tick_length_us = device_time.ticks_diff(
                device_time.ticks_us(), tick_start_us
            )
            ticks_until_next_frame = target_tick_length_us - tick_length_us
            if ticks_until_next_frame > 0:
                device_time.sleep_us(ticks_until_next_frame)
            
            elapsed_frame_count += 1
            if elapsed_frame_count % 200 == 0:
                elapsed_ticks_us = device_time.ticks_diff(
                    device_time.ticks_us(), elapsed_time_anchor_us
                )
                print(f'fps:{1_000_000 / (elapsed_ticks_us / elapsed_frame_count)}')
                elapsed_frame_count = 0
                elapsed_time_anchor_us = device_time.ticks_us()
