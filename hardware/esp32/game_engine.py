import time
from machine import Pin, SoftI2C, PWM, Timer
from hardware.esp32 import ssd1306

from game_device import GameAudio, GameDevice

i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=4000000)
display = ssd1306.SSD1306_I2C(128, 64, i2c)  # display object
button = Pin(4, Pin.IN, Pin.PULL_UP)
target_fps = 24
target_tick_length_us = 1_000_000 // target_fps

speaker_pwm = PWM(Pin(23))
AUDIO_BPM = 480
speaker_pwm.deinit()

pwm_max_duty = 2**16 - 1
pwm_volume_duty = pwm_max_duty // 2**6
pwm_off_duty = 0
melody_playing = False
melody_note_idx = 0
melody_duration_counter = 0
melody_freqs = []
melody_durations = []


def tim_cb(t):
    global melody_playing
    global melody_note_idx
    global melody_freqs
    global melody_durations
    global melody_duration_counter
    if not melody_playing:
        return

    if melody_duration_counter == 0:
        duration_counter = melody_durations[melody_note_idx]
    f = melody_freqs[melody_note_idx]

    if f == 0:
        speaker_pwm.duty_u16(pwm_off_duty)
    else:
        speaker_pwm.init(freq=f, duty_u16=pwm_volume_duty)

    duration_counter -= 1
    if duration_counter == 0:
        melody_note_idx = melody_note_idx + 1

    if melody_note_idx == len(melody_freqs):
        melody_playing = False


tim0 = Timer(0)
tim0.init(freq=int(AUDIO_BPM / 60), mode=Timer.PERIODIC, callback=tim_cb)


class PwmGameAudio(GameAudio):
    def __init__(self):
        self.melodies = []

    def load_melody(self, melody):
        freqs = [self.note_to_freq(mn[0], mn[1]) for mn in melody]
        durations = [mn[2] for mn in melody]
        self.melodies.append((freqs, durations))
        return len(self.melodies) - 1

    def play(self, melody_id):
        global melody_playing
        global melody_note_idx
        global melody_freqs
        global melody_durations
        global melody_duration_counter
        freqs, durations = self.melodies[melody_id]
        melody_freqs = freqs
        melody_durations = durations
        melody_duration_counter = 0
        melody_note_idx = 0
        melody_playing = True


class GameEngine:
    def __init__(self) -> None:
        self.device = GameDevice(time, display, button, PwmGameAudio())

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
                print(f"fps:{1_000_000 / (elapsed_ticks_us / elapsed_frame_count)}")
                elapsed_frame_count = 0
                elapsed_time_anchor_us = device_time.ticks_us()
