from array import array
import math
import pygame
from sys import exit
from typing import Type
from game_device import GameDevice, GameDisplay, GameTime, GameButton, GameAudio
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

        # Pseudo pixel grid - for fun
        if self.scale > 4:
            for i in range(0, self.screen.get_width()):
                for j in range(0, self.screen.get_height()):
                    if i % self.scale == 0 or j % self.scale == 0:
                        self.screen.set_at((i, j), self.colors[0])

        pygame.display.flip()

    def fill(self, col):
        self.buffer.fill(self.colors[col])

    def text(self, string, x, y, col=1):
        if self.last_surface_text != string:
            self.last_surface_text = string
            self.last_text_surface = self.font.render(string, False, self.colors[col])
        self.buffer.blit(self.last_text_surface, [x, y], None)

    def center_text(self, string, col):
        strlen = len(string) * 8
        self.text(string, (self.width - strlen) // 2, (self.height - 8) // 2, col)

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

    def blit_onto(self, buf_src: pygame.Surface, buf_dest: pygame.Surface, x, y):
        buf_dest.blit(buf_src, [x, y])


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


AUDIO_BIT_DEPTH = 8
AUDIO_SAMPLE_RATE = 5512
AUDIO_BPM = 480


class MockGameAudio(GameAudio):
    def __init__(self, mute=False) -> None:
        pygame.mixer.pre_init(AUDIO_SAMPLE_RATE, -AUDIO_BIT_DEPTH, 1)
        self.mute = mute
        self.sounds = []
        self.last_played_interruptable = True

    def play(self, sound_id, interruptable=True):
        if self.mute:
            pygame.mixer.stop()
            return

        if pygame.mixer.get_busy():
            if self.last_played_interruptable:
                pygame.mixer.stop()
            else:
                return

        self.last_played_interruptable = interruptable
        self.sounds[sound_id].play(loops=0)

    def load_melody(self, melody):
        sample_rate = AUDIO_SAMPLE_RATE
        bpm = AUDIO_BPM
        note_fade_in_out_length = 0.03
        note_fade_in_out_samples = int(note_fade_in_out_length * sample_rate)
        note_length_seconds = 60 / bpm
        melody_length_seconds = sum([m[2] for m in melody]) * note_length_seconds
        n_samples = int(round(melody_length_seconds * sample_rate))
        buf = [0 for z in range(0, n_samples)]
        max_sample = 2 ** (AUDIO_BIT_DEPTH - 1) - 1
        note_starts_at_sample = 0
        for m in melody:
            octave, note, duration = m
            f = self.note_to_freq(octave, note)
            samples_for_note = int(duration * note_length_seconds * sample_rate)
            for note_sample_iter in range(samples_for_note):
                curr_sample = note_starts_at_sample + note_sample_iter
                t = float(curr_sample) / sample_rate  # time in seconds
                dampen_factor = 1

                if note_sample_iter <= note_fade_in_out_samples:
                    dampen_factor = note_sample_iter / note_fade_in_out_samples
                if note_sample_iter >= samples_for_note - note_fade_in_out_samples:
                    dampen_factor = (
                        samples_for_note - note_sample_iter
                    ) / note_fade_in_out_samples

                # grab the x-coordinate of the sine wave at a given time, while constraining the sample to what our mixer is set to with "bits"
                buf[curr_sample] = int(
                    round(max_sample * math.sin(2 * math.pi * f * t) * dampen_factor)
                )
            note_starts_at_sample += samples_for_note
        sound = pygame.mixer.Sound(array("b" if AUDIO_BIT_DEPTH == 8 else "h", buf))
        self.sounds.append(sound)
        return len(self.sounds) - 1


class GameEngine:
    def __init__(self) -> None:
        self.audio = MockGameAudio(mute=False)
        pygame.init()
        self.display = MockGameDisplay(128, 64, 3)
        self.time = MockTime()
        self.button = MockButton()
        self.device = GameDevice(self.time, self.display, self.button, self.audio)

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
