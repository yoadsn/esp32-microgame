from math import pi, sin
from random import random

from game_device import GameDevice
from game_logic import BaseGameLogic
from games.duel.env import GAME_ROOT_DIR
from games.duel.sound import (
    Sound,
    INTRO_MELODY,
    HIT_OTHER_MELODY,
    HIT_MELODY,
    CAPTURE_UFO_MELODY,
    SHOOT_MELODY,
)
from games.duel.ufos import Ufo, UfoTypes, get_random_ufo_type
from games.duel.player import (
    Player,
    PLAYER_POSITION_TOP,
    PLAYER_POSITION_BOTTOM,
)
from games.duel.bot_player import ComputerController


FIELD_WIDTH = 116

GST_INIT = -2
GST_PRELOADER = -1
GST_ROUND_INIT = 0
GST_ROUND_PRE_RUN = 1
GST_ROUND_RUN = 2
GST_ROUND_ENDED = 3
BANNER_SHOW_TIME_MS = 3500

GST_ROUNDED_ENDED_DELAY_MS = 2000

MAX_UFOS_IN_GAME = 2
UFO_MIN_TIME_BETWEEN_SPAWNS_MS = 4000
UFO_SPAWN_CHANCE = 0.05  # 5%


class GameLogic(BaseGameLogic):
    def __init__(self, device: GameDevice) -> None:
        self.screen_width = device.display.width
        self.screen_height = device.display.height
        super().__init__(device)

    def load(self):
        self.field_width = FIELD_WIDTH
        self.field_start = (self.device.display.width - self.field_width) // 2
        self.field_end = self.device.display.width - self.field_start

        print("Loading game...")

        # Load only mandatory assets for the preloader
        self.intro_sound = Sound(
            self.device.audio, self.device.audio.load_melody(INTRO_MELODY), False
        )

        self.banner_sprite = self.device.load_display_asset(
            GAME_ROOT_DIR + "/assets/banner.pbm"
        )

        self.game_state = GST_INIT

        print("game loading done")

    def preload_assets(self):
        self.shoot_sound = Sound(
            self.device.audio, self.device.audio.load_melody(SHOOT_MELODY)
        )
        self.hit_sound = Sound(
            self.device.audio, self.device.audio.load_melody(HIT_MELODY)
        )
        self.hit_other_sound = Sound(
            self.device.audio, self.device.audio.load_melody(HIT_OTHER_MELODY)
        )
        self.capture_ufo_sound = Sound(
            self.device.audio, self.device.audio.load_melody(CAPTURE_UFO_MELODY)
        )

        # Crate a ship and a UFO to force them to load assets
        # for the first time
        Player(self.device, 0, 1, 0, 1)
        Ufo(self.device, 0, 1, 0)
        # No need to storem them since they are not part of the game

    def initialize_round(self):
        print("round init")
        self.round_won = False
        self.count_down_to_invert = 0
        self.bot_player = Player(
            self.device,
            self.field_start,
            self.field_end,
            self.field_end,  # bezel
            self.device.display.width,  # bezel
            position=PLAYER_POSITION_TOP,
        )
        self.human_player = Player(
            self.device,
            self.field_start,
            self.field_end,
            0,  # bezel
            self.field_start,  # bezel
            position=PLAYER_POSITION_BOTTOM,
            shoot_sound=self.shoot_sound,
        )
        self.npc = ComputerController(self.bot_player)
        self.ufos: list[Ufo] = []
        self.last_ufo_spawn_time_ms = 0

    def spawn_ufos(self):
        curr_ufo_count = len(self.ufos)
        if curr_ufo_count < MAX_UFOS_IN_GAME:
            time = self.device.time
            time_since_last_spawn = time.ticks_diff(
                time.ticks_ms(), self.last_ufo_spawn_time_ms
            )
            if (
                time_since_last_spawn > UFO_MIN_TIME_BETWEEN_SPAWNS_MS
                or self.last_ufo_spawn_time_ms == 0
            ):
                # prob is exp decreasing as UFOs are spawned
                ufo_spawn_prob = pow(UFO_SPAWN_CHANCE, curr_ufo_count + 1)
                if random() < ufo_spawn_prob:  # spawn chance
                    self.last_ufo_spawn_time_ms = time.ticks_ms()
                    ufo_type = get_random_ufo_type()
                    ufo_direction = 1 if random() < 0.5 else -1
                    self.ufos.append(
                        Ufo(
                            self.device,
                            self.field_start,
                            self.field_end,
                            self.screen_height // 2,
                            ufo_type,
                            ufo_direction,
                        )
                    )

    def play(self):
        time = self.device.time
        # Progress States
        next_state = curr_state = self.game_state
        now = time.ticks_ms()
        button_pressed = self.device.button.value() == 0

        if curr_state == GST_ROUND_RUN:
            if self.bot_player.check_exploded() or self.human_player.check_exploded():
                next_state = GST_ROUND_ENDED

        elif curr_state == GST_ROUND_INIT:
            next_state = GST_ROUND_PRE_RUN

        elif curr_state == GST_ROUND_PRE_RUN:
            if button_pressed:
                next_state = GST_ROUND_RUN

        elif curr_state == GST_ROUND_ENDED:
            if time.ticks_diff(now, self.game_state_start) > GST_ROUNDED_ENDED_DELAY_MS:
                next_state = GST_PRELOADER
        elif curr_state == GST_INIT:
            next_state = GST_PRELOADER
        else:
            next_state = GST_ROUND_INIT

        prev_state = curr_state
        if next_state != curr_state:
            self.game_state_start = now
            self.game_state = curr_state = next_state

        # Act
        if curr_state == GST_PRELOADER:
            self.intro_sound.play()
            # allow the banner to splash as we prepare for a new round
            self.banner_splash_start_time_ms = self.device.time.ticks_ms()
        elif curr_state == GST_ROUND_INIT:
            self.preload_assets()
            self.initialize_round()

        elif curr_state == GST_ROUND_ENDED:
            self.round_won = self.bot_player.check_exploded()

        elif curr_state == GST_ROUND_RUN:
            if prev_state == GST_ROUND_PRE_RUN:
                self.start_game_tick = self.device.time.ticks_ms()

            self.human_player.play(button_pressed)
            self.npc.play()
            self.spawn_ufos()

    def move(self):
        if self.game_state == GST_ROUND_RUN:
            # Move players if in defensive mode
            self.human_player.move()
            self.bot_player.move()

            # missile-player hits
            self.hit_player(self.human_player, self.bot_player)
            self.hit_player(self.bot_player, self.human_player)

            # move UFOs
            for ufo in self.ufos:
                if ufo:
                    ufo.move()
                    # missile-ufo hits
                    self.hit_ufo(self.human_player, ufo)
                    self.hit_ufo(self.bot_player, ufo)

                    # out of bounds UFO dead
                    if ufo.x < self.field_start or ufo.x > self.field_end - ufo.width:
                        ufo.dead = True

            # Remove captured/dead UFOs - managed by players moving fwd if captured
            self.ufos = [
                ufo for ufo in self.ufos if not ufo.is_cpatured() and not ufo.dead
            ]

    def draw(self):
        time = self.device.time
        display = self.device.display

        # Set default contrast
        display.contrast(255)

        if self.game_state == GST_PRELOADER or self.game_state == GST_ROUND_INIT:
            display.blit(self.banner_sprite.buffer, 0, 0)
        elif self.game_state == GST_ROUND_PRE_RUN:
            time_since_banner_shown = time.ticks_diff(
                time.ticks_ms(), self.banner_splash_start_time_ms
            )
            if time_since_banner_shown < BANNER_SHOW_TIME_MS:
                display.blit(self.banner_sprite.buffer, 0, 0)
            else:
                display.fill(0)
                display.center_text("Press Start", 1)
                display.contrast(135 + int(sin(time.ticks_ms() / 500 * pi) * 12) * 10)
        else:
            display.fill(0)
            self.bot_player.draw()
            self.human_player.draw()

            if self.game_state == GST_ROUND_ENDED:
                if self.round_won:
                    display.center_text("Victory", 1)
                else:
                    display.center_text("Defeat", 1)
            else:
                # move UFOs
                for ufo in self.ufos:
                    if ufo:
                        ufo.draw()

            if self.count_down_to_invert > 0:
                if self.game_state == GST_ROUND_ENDED:
                    self.count_down_to_invert = 0
                    display.invert(0)
                else:
                    display.invert(1)
                    self.count_down_to_invert -= 1
                    if self.count_down_to_invert == 0:
                        display.invert(0)

        display.show()

    def hit_player(self, shooter: Player, target: Player):
        if shooter.missile:
            proj_rect = shooter.missile.get_hit_rect()
            if target.check_hit(proj_rect):
                target.update_power(-1)
                if shooter == self.human_player:
                    self.hit_other_sound.play()
                else:
                    self.hit_sound.play()
                shooter.missile = None  # Can't hit again!
                self.count_down_to_invert = 5

    def hit_ufo(self, shooter: Player, target: Ufo):
        if shooter.missile and not target.is_cpatured():
            proj_rect = shooter.missile.get_hit_rect()
            if target.check_hit(proj_rect):
                if target.type == UfoTypes.DAMAGE or target.type == UfoTypes.POWER:
                    shooter.capture_ufo(None)
                    if target.type == UfoTypes.DAMAGE:
                        shooter.update_power(-1)
                        self.count_down_to_invert = 5
                        self.hit_sound.play()
                    else:
                        shooter.update_power(1)
                        self.capture_ufo_sound.play()
                    target.dead = True
                else:
                    shooter.capture_ufo(target)
                    self.capture_ufo_sound.play()

                shooter.missile = None  # Can't hit again!

    def game_tick(self):
        self.play()
        self.move()
        self.draw()
