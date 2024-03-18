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
speaker_pwm.deinit()
AUDIO_BPM = 480

pwm_max_duty = 2**16 - 1
pwm_volume_duty = pwm_max_duty // 2**6
pwm_off_duty = 0
melodies_queue = []


def tim_cb(t):
    global melodies_queue

    if len(melodies_queue) == 0:
        speaker_pwm.deinit()
        return

    freqs, durations, melody_note_idx, melody_duration_counter, play_request_id, interruptable = (
        melodies_queue[0]
    )
    duration_counter = melody_duration_counter
    if duration_counter == 0:
        duration_counter = durations[melody_note_idx]
    f = freqs[melody_note_idx]

    # silence note - off duty
    if f == 0:
        speaker_pwm.duty_u16(pwm_off_duty)
    else:
        speaker_pwm.init(freq=f, duty_u16=pwm_volume_duty)

    # next play duration of note
    duration_counter -= 1

    # End of note? move to next note
    if duration_counter <= 0:
        melody_note_idx = melody_note_idx + 1

    # melody is done playing
    if melody_note_idx == len(freqs):
        # remove from queue
        melodies_queue.pop(0)
    else:
        # ensure the item in the queue is still the item
        # being played
        if melodies_queue[0][4] == play_request_id:
            melodies_queue[0] = (
                freqs,
                durations,
                melody_note_idx,
                duration_counter,
                play_request_id,
                interruptable
            )
        # the queue has been altered await nexy cycle to resync with it
        else:
            pass


tim0 = Timer(0)
tim0.init(freq=int(AUDIO_BPM / 60), mode=Timer.PERIODIC, callback=tim_cb)


class PwmGameAudio(GameAudio):
    def __init__(self):
        self.melodies = []
        self.play_request_id = 0

    def load_melody(self, melody):
        freqs = [self.note_to_freq(mn[0], mn[1]) for mn in melody]
        durations = [mn[2] for mn in melody]
        self.melodies.append((freqs, durations))
        return len(self.melodies) - 1

    def play(self, melody_id, interruptable=True):
        global melodies_queue

        self.play_request_id += 1
        freqs, durations = self.melodies[melody_id]
        melody_queue_item = (
            freqs,
            durations,
            0,
            0,
            self.play_request_id,
            interruptable,
        )  # (freqs, durations, note idx, duration counter)

        if len(melodies_queue) > 0 and melodies_queue[0][5]:
            melodies_queue.clear()

        melodies_queue.append(melody_queue_item)


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
