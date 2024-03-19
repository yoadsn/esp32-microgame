from games.duel.env import GAME_ROOT_DIR
from games.duel.sound import Sound
from games.duel.missile import BASE_MISSILE_SPEED, Missile
from game_device import GameDevice, GameDisplayAsset
from games.duel.bars import (
    ChargeBar,
    PowerBar,
    BAR_FILL_DIRECTION_BTT,
    BAR_FILL_DIRECTION_TTB,
)
from games.duel.ufos import Ufo, UfoTypes

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


SHIP_SPRITE_HULL = 0
SHIP_SPRITE_WING_TIP_LEFT = 1
SHIP_SPRITE_WING_TIP_RIGHT = 2
SHIP_SPRITE_WING_EXT = 3
SHIP_SPRITES_TTB = []
SHIP_SPRITES_BTT = []


class Player:
    def __init__(
        self,
        device: GameDevice,
        field_start: int,
        field_end: int,
        bezel_start: int,
        bezel_end: int,
        power_points: int = PLAYER_BASE_POWER_POINTS,
        position: int = PLAYER_POSITION_TOP,
        initialSpeed: int = PLAYER_INITIAL_SPEED_PX_F,
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
        self.load_display_assets()
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

        self.ufo_prison_start_x = self.bezel_start
        self.ufo_prison_end_x = self.bezel_end
        self.ufo_prison_start_y = bar_height if position == PLAYER_POSITION_TOP else 0
        self.ufo_prison_end_y = (
            self.display.height - 1 if position == PLAYER_POSITION_TOP else bar_height
        )

        self.update_power(0)

    def load_display_assets(self):
        global SHIP_SPRITES_TTB
        global SHIP_SPRITES_BTT
        # Used cached assets when possible
        if len(SHIP_SPRITES_TTB) == 0:
            print("Loading ship assets...")
            device = self.device
            for btt in [False, True]:
                flip_v = btt
                store = SHIP_SPRITES_BTT if btt else SHIP_SPRITES_TTB
                store.append(
                    device.load_display_asset(
                        GAME_ROOT_DIR + "/assets/ship-hull.pbm", flip_v=flip_v
                    )
                )
                store.append(
                    device.load_display_asset(
                        GAME_ROOT_DIR + "/assets/ship-wingtip.pbm", flip_v=flip_v
                    )
                )
                store.append(
                    device.load_display_asset(
                        GAME_ROOT_DIR + "/assets/ship-wingtip.pbm",
                        flip_v=flip_v,
                        flip_h=True,
                    )
                )
                store.append(
                    device.load_display_asset(
                        GAME_ROOT_DIR + "/assets/ship-wing-ext.pbm", flip_v=flip_v
                    )
                )
            print("done")

        self.sprites_store = (
            SHIP_SPRITES_TTB
            if self.position == PLAYER_POSITION_TOP
            else SHIP_SPRITES_BTT
        )

    def init_display_assets(self):
        self.ship_hull_sprite = self.sprites_store[SHIP_SPRITE_HULL]
        self.ship_wing_ext_sprite = self.sprites_store[SHIP_SPRITE_WING_EXT]
        self.ship_wingtip_left_sprite = self.sprites_store[SHIP_SPRITE_WING_TIP_LEFT]
        self.ship_wingtip_right_sprite = self.sprites_store[SHIP_SPRITE_WING_TIP_RIGHT]

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
                        charge_time = CHARGE_TO_FIRE_WAIT_PER_POWER_MS // 3
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
                speed=(
                    BASE_MISSILE_SPEED * 2
                    if self.has_ufo_type(UfoTypes.RAPID_FIRE)
                    else BASE_MISSILE_SPEED
                ),
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
        player_half_width = self.player_width // 2
        limit_x_start = self.field_start + player_half_width
        limit_x_end = self.field_end - player_half_width
        height = self.display.height
        curr_state = self.play_state

        if curr_state == PST_EXPLODED:
            return

        if curr_state == PST_DEFENSIVE:
            # Normal defensive movement logic
            speed = self.vx
            if self.has_ufo_type(UfoTypes.SLOW):
                speed = speed * 0.25
            self.x += speed
            if self.x <= limit_x_start:
                self.x = limit_x_start
                self.vx *= -1
            elif self.x >= limit_x_end:
                self.x = limit_x_end
                self.vx *= -1

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
            draw_y = (
                self.y if self.position == PLAYER_POSITION_TOP else int(self.y) - dh + 1
            )
            draw_start_x = int(self.x) - ship_helf_width
            display.blit(ship_sprite.buffer, draw_start_x, draw_y)
            if self.has_ufo_type(UfoTypes.SHIELD):
                shield_y = (
                    dh + 2 if self.position == PLAYER_POSITION_TOP else draw_y - 2
                )
                display.line(
                    draw_start_x, shield_y, draw_start_x + ship_sprite.w, shield_y, 1
                )

        # Draw the missile
        if self.missile:
            self.missile.draw()

        # Draw any cpatured ufos
        if self.ufo:
            self.ufo.draw(
                self.ufo_prison_start_x,
                self.ufo_prison_start_y,
                self.ufo_prison_end_x,
                self.ufo_prison_end_y,
            )

        if curr_state == PST_CHARGING:
            # Draw Charging progress
            self.charge_bar.draw(self.charge_pct)
        else:
            # Draw power
            self.power_bar.draw(self.power_points)
