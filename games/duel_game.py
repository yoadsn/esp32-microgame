import random
from game_device import GameDevice
from game_logic import BaseGameLogic

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
PLAYER_INITIAL_SPEED_PX_F = 3
PLAYER_BASE_POWER_POINTS = 20
PLAYER_BASE_LENGTH_PX = 40
PLAYER_MIN_BASE_LENGTH_PX = 5

PROJECTILE_BLAST_RADIUS = 2
PROJECTILE_SPEED = 2


class Sound:
    def __init__(self, audio, sound, interruptable=True) -> None:
        self.audio = audio
        self.sound = sound
        self.interruptable = interruptable

    def play(self):
        self.audio.play(self.sound, self.interruptable)


class Projectile:
    def __init__(self, display, x, y, direction):
        self.display = display
        self.x = x
        self.y = y
        self.direction = direction

    def move(self):
        self.y += self.direction * PROJECTILE_SPEED

    def draw(self):
        self.display.pixel(int(self.x), int(self.y), 1)

    def get_hit_rect(self):
        return (
            self.x - PROJECTILE_BLAST_RADIUS,
            self.y - PROJECTILE_BLAST_RADIUS,
            self.x + PROJECTILE_BLAST_RADIUS,
            self.y + PROJECTILE_BLAST_RADIUS,
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


class Player:
    def __init__(
        self,
        time,
        display,
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
        self.time = time
        self.display = display

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
        self.y = 1 if position == PLAYER_POSITION_TOP else display.height - 2

        # State initialization
        self.play_state: int = PST_INIT
        self.play_state_start: int = 0
        self.power_points = power_points

        self.sprite = display.get_buffer(
            bytearray(
                (
                    0b0000_0000,
                    0b0000_0000,
                    0b0011_1100,
                    0b0011_1100,
                    0b1110_1110,
                    0b0111_0111,
                    0b0000_0011,
                    0b1100_0000,
                    0b0000_0001,
                    0b1000_0000,
                )
            ),
            16,
            5,
        )

        self.vx = initialSpeed
        self.projectile = None
        self.charge_pct = 0

        # Charge / Power Bars
        bar_height = display.height // 2
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
                display.height - bar_height,
                bar_width,
                bar_height,
            )
        )
        self.charge_bar = ChargeBar(
            display,
            bar_direction,
            bar_rect,
        )
        self.power_bar = PowerBar(
            display,
            bar_direction,
            bar_rect,
            power_points,
        )

        self.update_power(0)

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
                    if time_in_state > STOP_TO_CHARGE_WAIT_MS and not self.projectile:
                        next_state = PST_CHARGING
                elif curr_state == PST_CHARGING:
                    next_state = PST_CHARGING
                    self.charge_pct = time_in_state / float(
                        CHARGE_TO_FIRE_WAIT_PER_POWER_MS * self.power_points
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

            self.projectile = Projectile(
                self.display,
                self.x,
                self.y,
                self.direction,  # go up (pos 1) or down (pos 0)
            )

    def check_hit(self, rect):
        if self.check_exploded():
            return False

        x1, y1, x2, y2 = rect
        # Why the ugly nested if? To save on calcs
        if y1 <= self.y and y2 >= self.y:
            player_half_width = self.player_width // 2
            player_start_x = self.x - player_half_width
            if x2 >= player_start_x:
                player_end_x = self.x + player_half_width
                if x1 <= player_end_x:
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
        self.charge_bar.set_full_charge_pct(
            self.power_points / PLAYER_BASE_POWER_POINTS
        )

    def move(self):
        field_start = self.field_start
        field_end = self.field_end
        width = self.field_width
        height = self.display.height
        curr_state = self.play_state

        if curr_state == PST_EXPLODED:
            return

        player_half_width = self.player_width // 2
        if curr_state == PST_DEFENSIVE:
            # Normal defensive movement logic
            self.x += self.vx
            if (
                self.x <= field_start + player_half_width
                or self.x >= field_end - player_half_width
            ):
                self.vx *= -1
                self.x = self.x

        # Move projectile if it exists
        if self.projectile:
            self.projectile.move()
            if self.projectile.y <= 0 or self.projectile.y >= height:
                self.projectile = None  # Remove projectile when it leaves the screen

    def draw(self):
        curr_state = self.play_state
        display = self.display

        x, y = self.x, self.y

        # player bar
        if curr_state == PST_EXPLODED:
            display.rect(x, y, 1, 1, 1)
        else:
            player_half_width = self.player_width // 2
            """ display.blit(
                self.sprite,
                self.x - 8,
                self.y + (0 if self.position == PLAYER_POSITION_TOP else -5),
            ) """
            display.line(
                int(x - player_half_width), y, int(x + player_half_width), y, 1
            )

        # Draw the projectile
        if self.projectile:
            self.projectile.draw()

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

        if not self.player.projectile:
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


class GameLogic(BaseGameLogic):
    def __init__(self, device: GameDevice) -> None:
        self.screen_width = device.display.width
        self.screen_height = device.display.height
        super().__init__(device)

    def load(self):
        print("game loaded")
        self.field_width = FIELD_WIDTH
        self.field_start = (self.device.display.width - self.field_width) // 2
        self.field_end = self.device.display.width - self.field_start

        self.shoot_sound = Sound(self.device.audio, self.device.audio.load_melody(SHOOT_MELODY))
        self.hit_sound = Sound(self.device.audio, self.device.audio.load_melody(HIT_MELODY))

        self.game_state = GST_INIT

    def initialize_round(self):
        print("round init")
        self.round_won = False
        self.count_down_to_invert = 0
        self.top_player = Player(
            self.device.time,
            self.device.display,
            self.field_start,
            self.field_end,
            0,  # bezel
            self.field_start,  # bezel
            position=PLAYER_POSITION_TOP,
            power_points=PLAYER_BASE_POWER_POINTS,
            initialSpeed=PLAYER_INITIAL_SPEED_PX_F,
            shoot_sound=self.shoot_sound,
        )
        self.bottom_player = Player(
            self.device.time,
            self.device.display,
            self.field_start,
            self.field_end,
            self.field_end,  # bezel
            self.device.display.width,  # bezel
            position=PLAYER_POSITION_BOTTOM,
            power_points=PLAYER_BASE_POWER_POINTS,
            initialSpeed=PLAYER_INITIAL_SPEED_PX_F,
        )
        self.npc = ComputerController(self.bottom_player)

    def play(self):
        time = self.device.time
        # Progress States
        next_state = curr_state = self.game_state
        now = time.ticks_ms()
        button_pressed = self.device.button.value() == 0

        if curr_state == GST_ROUND_RUN:
            if self.top_player.check_exploded() or self.bottom_player.check_exploded():
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
            self.round_won = self.bottom_player.check_exploded()

        elif curr_state == GST_ROUND_RUN:
            if prev_state == GST_ROUND_PRE_RUN:
                self.start_game_tick = self.device.time.ticks_ms()

            self.top_player.play(button_pressed)
            self.npc.play()

    def move(self):
        if self.game_state == GST_ROUND_RUN:
            # Move players if in defensive mode
            self.top_player.move()
            self.bottom_player.move()

            # projectile hits
            self.hit(self.top_player, self.bottom_player)
            self.hit(self.bottom_player, self.top_player)

    def draw(self):
        display = self.device.display
        # Clear display and redraw players
        display.fill(0)

        display.rect(
            self.field_start, 0, self.field_width, self.device.display.height, 1
        )

        if self.game_state == GST_ROUND_PRE_RUN:
            display.center_text("Press Start", 1)
        elif self.game_state == GST_ROUND_ENDED:
            if self.round_won:
                display.center_text("Won!", 1)
            else:
                display.center_text("Lost..", 1)

        self.top_player.draw()
        self.bottom_player.draw()

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

    def hit(self, shooter: Player, target: Player):
        if shooter.projectile:
            proj_rect = shooter.projectile.get_hit_rect()
            if target.check_hit(proj_rect):
                target.update_power(-1)
                self.hit_sound.play()
                shooter.projectile = None  # Can't hit again!
                self.count_down_to_invert = 5

    def game_tick(self):
        self.play()
        self.move()
        self.draw()
