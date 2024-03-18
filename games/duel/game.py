from random import random
from game_device import GameDevice, GameDisplayAsset
from game_logic import BaseGameLogic
from games.duel.ufos import Ufo, UfoTypes, get_random_ufo_type

game_root_dir = "./games/duel"

FIELD_WIDTH = 116

PLAYER_POSITION_TOP = 0
PLAYER_POSITION_BOTTOM = 1

PST_INIT = -1
PST_DEFENSIVE = 0
PST_STOPPED = 1
PST_CHARGING = 2
PST_FIRING = 3
PST_EXPLODED = 4

STOP_TO_CHARGE_WAIT_MS = 10
CHARGE_TO_FIRE_WAIT_PER_POWER_MS = 55
PLAYER_INITIAL_SPEED_PX_F = 4
PLAYER_BASE_POWER_POINTS = 10
PLAYER_BASE_LENGTH_PX = 40
PLAYER_MIN_BASE_LENGTH_PX = 12


class Sound:
    def __init__(self, audio, sound, interruptable=True) -> None:
        self.audio = audio
        self.sound = sound
        self.interruptable = interruptable

    def play(self):
        self.audio.play(self.sound, self.interruptable)


DEFAULT_MISSILE_BLAST_RADIUS = 2
BASE_MISSILE_SPEED = 3


class Missile:
    def __init__(
        self,
        display,
        x,
        y,
        direction_y,
        speed=BASE_MISSILE_SPEED,
        blast_radius=DEFAULT_MISSILE_BLAST_RADIUS,
    ):
        self.display = display
        self.x = x
        self.y = y
        self.direction_y = direction_y
        self.speed = speed
        self.blast_radius = blast_radius

    def move(self):
        if self.direction_y != 0:
            self.y += self.direction_y * self.speed

    def draw(self):
        self.display.pixel(int(self.x), int(self.y), 1)

    def get_hit_rect(self):
        return (
            self.x - self.blast_radius,
            self.y - self.blast_radius,
            self.x + self.blast_radius,
            self.y + self.blast_radius,
        )


BAR_FILL_DIRECTION_TTB = 1
BAR_FILL_DIRECTION_BTT = -1


class ProgressBar:
    def __init__(
        self,
        display,
        fill_direction: int,  # 1 with orientation -1 again
        rect,  # bounds of the bar
        show_max_line: bool = False,
    ):
        self.display = display
        self.fill_direction = fill_direction
        rect_x1, rect_y1, rect_w, rect_h = rect
        self.height = self.max_height = rect_h
        self.start_x = rect_x1
        self.width = rect_w
        # depends on fill direction
        self.start_y = (
            rect_y1 if fill_direction == BAR_FILL_DIRECTION_TTB else rect_y1 + rect_h
        )
        self.show_max_line = show_max_line
        if show_max_line:
            self.set_max_height(self.max_height)

    def set_max_height(self, new_max_height):
        self.max_height = new_max_height
        self.max_line_y = int(
            self.start_y + self.max_height - 1
            if self.fill_direction == BAR_FILL_DIRECTION_TTB
            else self.start_y - self.max_height + 1
        )

    def draw(self, fill):
        fill_height = fill
        self.display.fill_rect(
            self.start_x,
            (
                self.start_y
                if self.fill_direction == BAR_FILL_DIRECTION_TTB
                else self.start_y - fill_height
            ),
            self.width,
            fill_height,
            1,
        )

        if self.show_max_line:
            self.display.line(
                self.start_x,
                self.max_line_y,
                self.start_x + self.width - 1,
                self.max_line_y,
                1,
            )


class ChargeBar(ProgressBar):
    def __init__(
        self,
        display,
        fill_direction: int,
        rect,
    ):
        super().__init__(display, fill_direction, rect, True)
        self.full_charge_pct = 1

    def set_full_charge_pct(self, max_charge_pct):
        self.full_charge_pct = max_charge_pct
        super().set_max_height(self.height * self.full_charge_pct)

    def draw(self, pct):
        super().draw(int(self.height * pct * self.full_charge_pct))


class PowerBar(ProgressBar):
    def __init__(self, display, fill_direction: int, rect, max_power: int):
        self.max_power = max_power
        super().__init__(display, fill_direction, rect, False)

    def draw(self, power):
        super().draw(int(self.height * power / self.max_power))


SHOOT_MELODY = [(6, 1, 1), (5, 1, 1)]
HIT_MELODY = [(6, 7, 1), (4, 4, 1), (3, 1, 1)]
CAPTURE_UFO_MELODY = [(4, 3, 1), (5, 3, 1), (6, 3, 2)]


class Player:
    def __init__(
        self,
        device: GameDevice,
        field_start: int,
        field_end: int,
        bezel_start: int,
        bezel_end: int,
        power_points: int,
        position: int = PLAYER_POSITION_TOP,
        initialSpeed: int = 3,
        shoot_sound: Sound = None,
    ):
        # Game access
        self.device = device
        self.time = device.time
        self.display = device.display

        # Game Setup
        self.field_start = field_start
        self.field_end = field_end
        # May change in-game - so dynamic in theory
        self.field_width = field_end - field_start
        self.bezel_start = bezel_start
        self.bezel_end = bezel_end
        self.bezel_width = bezel_end - bezel_start

        # Assets
        self.shoot_sound = shoot_sound

        # Positioning
        self.position = position
        self.direction = 1 - self.position * 2  # 1 or -1
        self.x = self.field_width // 2
        self.y = 0 if position == PLAYER_POSITION_TOP else self.display.height - 1

        # State initialization
        self.play_state: int = PST_INIT
        self.play_state_start: int = 0
        self.power_points = power_points

        self.vx = initialSpeed
        self.missile = None
        self.ufo: Ufo = None
        self.charge_pct = 0

        # Display assets setup
        self.init_display_assets()

        # Charge / Power Bars
        bar_height = self.display.height // 2
        bar_width = self.bezel_width
        bar_direction = (
            BAR_FILL_DIRECTION_TTB
            if position == PLAYER_POSITION_TOP
            else BAR_FILL_DIRECTION_BTT
        )
        bar_rect = (
            (
                bezel_start,  # charge bar start x
                0,
                bar_width,
                bar_height,
            )
            if position == PLAYER_POSITION_TOP
            else (
                bezel_start,  # charge bar start x
                self.display.height - bar_height,
                bar_width,
                bar_height,
            )
        )
        self.charge_bar = ChargeBar(
            self.display,
            bar_direction,
            bar_rect,
        )
        self.power_bar = PowerBar(
            self.display,
            bar_direction,
            bar_rect,
            power_points,
        )

        self.update_power(0)

    def init_display_assets(self):
        device = self.device
        flip_v = self.position == PLAYER_POSITION_BOTTOM

        self.ship_hull_sprite = device.load_display_asset(
            game_root_dir + "/assets/ship-hull.pbm", flip_v=flip_v
        )
        self.ship_wing_ext_sprite = device.load_display_asset(
            game_root_dir + "/assets/ship-wing-ext.pbm", flip_v=flip_v
        )
        self.ship_wingtip_left_sprite = device.load_display_asset(
            game_root_dir + "/assets/ship-wingtip-left.pbm", flip_v=flip_v
        )
        self.ship_wingtip_right_sprite = device.load_display_asset(
            game_root_dir + "/assets/ship-wingtip-right.pbm", flip_v=flip_v
        )

    def build_ship_display_asset(self):
        display = self.display
        ship_hull_sprite = self.ship_hull_sprite
        left_wingtip_sprite = self.ship_wingtip_left_sprite
        right_wingtip_sprite = self.ship_wingtip_right_sprite
        wing_ext_sprite = self.ship_wing_ext_sprite

        target_w = int(self.player_width)
        middle_w = target_w // 2
        target_h = self.ship_hull_sprite.h
        full_ship_buffer = display.get_buffer(
            bytearray(((target_w + 7) // 8) * target_h),
            target_w,
            target_h,
        )
        ship_hull_start_x = middle_w - ship_hull_sprite.w // 2
        display.blit_onto(
            ship_hull_sprite.buffer,
            full_ship_buffer,
            ship_hull_start_x,
            0,
        )
        if target_w > ship_hull_sprite.w:
            display.blit_onto(left_wingtip_sprite.buffer, full_ship_buffer, 0, 0)
            display.blit_onto(
                right_wingtip_sprite.buffer,
                full_ship_buffer,
                target_w - left_wingtip_sprite.w,
                0,
            )

            if (
                target_w
                - left_wingtip_sprite.w
                - right_wingtip_sprite.w
                - ship_hull_sprite.w
                > 0
            ):
                for ext_pos_x in range(
                    left_wingtip_sprite.w, ship_hull_start_x, wing_ext_sprite.w
                ):
                    display.blit_onto(
                        wing_ext_sprite.buffer,
                        full_ship_buffer,
                        ext_pos_x,
                        0,
                    )
                    display.blit_onto(
                        wing_ext_sprite.buffer,
                        full_ship_buffer,
                        target_w - ext_pos_x - 1,
                        0,
                    )
        self.ship_sprite = GameDisplayAsset(full_ship_buffer, target_w, target_h)

    def play(self, button):
        # progress state machine
        curr_state = self.play_state
        next_state = PST_DEFENSIVE
        now = self.time.ticks_ms()
        self.charge_pct = 0

        if self.power_points == 0:
            next_state = PST_EXPLODED
        elif button:
            if curr_state == PST_DEFENSIVE or curr_state == PST_FIRING:
                next_state = PST_STOPPED
            else:
                time_in_state = self.time.ticks_diff(now, self.play_state_start)
                if curr_state == PST_STOPPED:
                    next_state = PST_STOPPED
                    if time_in_state > STOP_TO_CHARGE_WAIT_MS and not self.missile:
                        next_state = PST_CHARGING
                elif curr_state == PST_CHARGING:
                    next_state = PST_CHARGING
                    charge_time = CHARGE_TO_FIRE_WAIT_PER_POWER_MS
                    if self.has_ufo_type(UfoTypes.RAPID_FIRE):
                        charge_time = CHARGE_TO_FIRE_WAIT_PER_POWER_MS // 2
                    self.charge_pct = time_in_state / float(
                        charge_time * self.power_points
                    )
                    if self.charge_pct >= 1:
                        next_state = PST_FIRING

        if next_state != curr_state:
            self.play_state_start = self.time.ticks_ms()
            self.play_state = next_state

        # Act on state
        if self.play_state == PST_FIRING:
            if self.shoot_sound:
                self.shoot_sound.play()

            self.missile = Missile(
                self.display,
                self.x,
                self.y,
                direction_y=self.direction,
            )

        # Keep only live captured UFOs
        if self.ufo is not None and self.ufo.dead:
            self.release_ufo()

    def has_ufo_type(self, type: int):
        return self.ufo and self.ufo.type == type

    def check_hit(self, hit_rect):
        if self.check_exploded():
            return False

        if self.has_ufo_type(UfoTypes.SHIELD):
            return False

        x1, y1, x2, y2 = hit_rect
        player_y1 = (
            self.y
            if self.position == PLAYER_POSITION_TOP
            else self.y - self.player_height
        )
        # Why the ugly nested if? To save on calcs
        if y2 >= player_y1:
            player_y2 = (
                self.y + self.player_height
                if self.position == PLAYER_POSITION_TOP
                else self.y
            )
            if y1 <= player_y2:
                player_half_width = self.player_width // 2
                player_x1 = self.x - player_half_width
                if x2 >= player_x1:
                    player_x2 = self.x + player_half_width
                    if x1 <= player_x2:
                        return True
        return False

    def check_exploded(self):
        return self.play_state == PST_EXPLODED

    def update_power(self, power_diff):
        self.power_points += power_diff
        self.player_width = max(
            PLAYER_MIN_BASE_LENGTH_PX,
            PLAYER_BASE_LENGTH_PX * (self.power_points / PLAYER_BASE_POWER_POINTS),
        )
        self.player_height = self.ship_hull_sprite.h
        self.charge_bar.set_full_charge_pct(
            self.power_points / PLAYER_BASE_POWER_POINTS
        )
        self.build_ship_display_asset()

    def capture_ufo(self, ufo: Ufo):
        if self.ufo:
            self.release_ufo()

        # Game can decide to release our UFOs without
        # capturing another one
        if ufo is not None:
            ufo.set_captured()
            self.ufo = ufo

    def release_ufo(self):
        self.ufo = None

    def move(self):
        field_start = self.field_start
        field_end = self.field_end
        width = self.field_width
        height = self.display.height
        curr_state = self.play_state

        if curr_state == PST_EXPLODED:
            return

        player_half_width = self.player_width // 2
        if curr_state == PST_DEFENSIVE and not self.has_ufo_type(UfoTypes.FROZEN):
            # Normal defensive movement logic
            self.x += self.vx
            if (
                self.x <= field_start + player_half_width
                or self.x >= field_end - player_half_width
            ):
                self.vx *= -1
                self.x = self.x

        # Move projectile if it exists
        if self.missile:
            self.missile.move()
            if self.missile.y <= 0 or self.missile.y >= height:
                self.missile = None  # Remove projectile when it leaves the screen

        # Move any captured UFO
        if self.ufo:
            self.ufo.move()

    def draw(self):
        curr_state = self.play_state
        display = self.display

        # player bar
        if curr_state != PST_EXPLODED:
            ship_sprite = self.ship_sprite
            ship_helf_width = ship_sprite.w // 2
            dh = ship_sprite.h
            draw_y = self.y if self.position == PLAYER_POSITION_TOP else self.y - dh + 1
            display.blit(ship_sprite.buffer, self.x - ship_helf_width, draw_y)

        # Draw the missile
        if self.missile:
            self.missile.draw()

        # Draw any cpatured ufos
        if self.ufo:
            self.ufo.draw()

        if curr_state == PST_CHARGING:
            # Draw Charging progress
            self.charge_bar.draw(self.charge_pct)
        else:
            # Draw power
            self.power_bar.draw(self.power_points)


class ComputerController:
    def __init__(self, player):
        self.player = player
        self.last_shot_time = None  # Track the last time a projectile was shot

    def play(self):
        current_time = self.player.time.ticks_ms()
        if self.last_shot_time is None:
            self.last_shot_time = current_time

        if not self.player.missile:
            # Check if at least 3 seconds have passed since the last shot
            if (
                self.last_shot_time is None
                or (current_time - self.last_shot_time) >= 3000
            ):
                self.player.play(True)
            else:
                self.player.play(False)
        else:  # If not in defensive mode, assume offensive mode
            self.last_shot_time = current_time
            self.player.play(False)


GST_INIT = -1
GST_ROUND_INIT = 0
GST_ROUND_PRE_RUN = 1
GST_ROUND_RUN = 2
GST_ROUND_ENDED = 3

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

        self.shoot_sound = Sound(
            self.device.audio, self.device.audio.load_melody(SHOOT_MELODY)
        )
        self.hit_sound = Sound(
            self.device.audio, self.device.audio.load_melody(HIT_MELODY)
        )
        self.capture_ufo_sound = Sound(
            self.device.audio, self.device.audio.load_melody(CAPTURE_UFO_MELODY)
        )

        self.game_state = GST_INIT

        print("game loaded")

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
            power_points=PLAYER_BASE_POWER_POINTS,
            initialSpeed=PLAYER_INITIAL_SPEED_PX_F,
        )
        self.human_player = Player(
            self.device,
            self.field_start,
            self.field_end,
            0,  # bezel
            self.field_start,  # bezel
            position=PLAYER_POSITION_BOTTOM,
            power_points=PLAYER_BASE_POWER_POINTS,
            initialSpeed=PLAYER_INITIAL_SPEED_PX_F,
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
            if time_since_last_spawn > UFO_MIN_TIME_BETWEEN_SPAWNS_MS:
                # prob is exp decreasing as UFOs are spawned
                ufo_spawn_prob = pow(UFO_SPAWN_CHANCE, curr_ufo_count + 1)
                if random() < ufo_spawn_prob:  # 5% spawn chance
                    self.last_ufo_spawn_time_ms = time.ticks_ms()
                    ufo_type = get_random_ufo_type()
                    ufo_direction = 1 if random() < 0.5 else -1
                    ufo_x_start = (
                        self.field_start if ufo_direction == 1 else self.field_end - 1
                    )
                    self.ufos.append(
                        Ufo(
                            self.device,
                            ufo_x_start,
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
                next_state = GST_ROUND_INIT
        else:
            next_state = GST_ROUND_INIT

        prev_state = curr_state
        if next_state != curr_state:
            self.game_state_start = now
            self.game_state = curr_state = next_state

        # Act
        if curr_state == GST_ROUND_INIT:
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
        display = self.device.display
        # Clear display and redraw players
        display.fill(0)

        display.line(
            self.field_start, 0, self.field_start, self.device.display.height, 1
        )
        display.line(self.field_end, 0, self.field_end, self.device.display.height, 1)

        if self.game_state == GST_ROUND_PRE_RUN:
            display.center_text("Press Start", 1)
        elif self.game_state == GST_ROUND_ENDED:
            if self.round_won:
                display.center_text("Won!", 1)
            else:
                display.center_text("Lost..", 1)

        self.bot_player.draw()
        self.human_player.draw()

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
                self.hit_sound.play()
                shooter.missile = None  # Can't hit again!
                self.count_down_to_invert = 5

    def hit_ufo(self, shooter: Player, target: Ufo):
        if shooter.missile and not target.is_cpatured():
            proj_rect = shooter.missile.get_hit_rect()
            if target.check_hit(proj_rect):
                if target.type == UfoTypes.DAMAGE:
                    shooter.capture_ufo(None)
                    shooter.update_power(-1)
                    self.count_down_to_invert = 5
                    self.hit_sound.play()
                    target.dead = True
                else:
                    shooter.capture_ufo(target)
                    self.capture_ufo_sound.play()

                shooter.missile = None  # Can't hit again!

    def game_tick(self):
        self.play()
        self.move()
        self.draw()
