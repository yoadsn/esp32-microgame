import random
from game_device import GameDevice
from game_logic import BaseGameLogic


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


class Projectile:
    def __init__(self, display, x, y, direction):
        self.display = display
        self.x = x
        self.y = y
        self.direction = direction  # 1 for downwards, -1 for upwards

    def move(self):
        self.y += self.direction  # Move the projectile 1 pixel per 5 frames

    def draw(self):
        self.display.pixel(int(self.x), int(self.y), 1)

    def get_hit_rect(self):
        return (
            self.x - PROJECTILE_BLAST_RADIUS,
            self.y - PROJECTILE_BLAST_RADIUS,
            self.x + PROJECTILE_BLAST_RADIUS,
            self.y + PROJECTILE_BLAST_RADIUS,
        )


class Player:
    def __init__(self, time, display, power_points, position="top", initialSpeed=3):
        # Game access
        self.time = time
        self.display = display

        # State initialization
        self.play_state: int = PST_INIT
        self.play_state_start: int = 0

        self.power_points = power_points
        self.position = position

        self.x = display.width // 2
        self.y = 1 if position == "top" else display.height - 2
        self.vx = initialSpeed
        self.building_cannon = False
        self.reverting_to_defensive = False
        self.cannon_height = 0
        self.projectile = None

    def play(self, button):
        # progress state machine
        curr_state = self.play_state
        next_state = PST_DEFENSIVE
        now = self.time.ticks_ms()

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
                        self.charge_pct = 0
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

        self.player_width = max(
            PLAYER_MIN_BASE_LENGTH_PX,
            PLAYER_BASE_LENGTH_PX * (self.power_points / PLAYER_BASE_POWER_POINTS),
        )

        # Act on state
        if self.play_state == PST_FIRING:
            direction = 1 if self.position == "top" else -1
            self.projectile = Projectile(
                self.display,
                self.x,
                self.y,
                direction,
            )
            self.power_points -= 1  # Lose one power point after shooting

    def check_hit(self, rect):
        if self.play_state == PST_EXPLODED:
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

    def move(self):
        width = self.display.width
        height = self.display.height
        curr_state = self.play_state

        if curr_state == PST_EXPLODED:
            return

        player_half_width = self.player_width // 2
        if curr_state == PST_DEFENSIVE:
            # Normal defensive movement logic
            self.x += self.vx
            if self.x <= player_half_width or self.x >= width - player_half_width:
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
            display.line(
                int(x - player_half_width), y, int(x + player_half_width), y, 1
            )

        # Draw the cannon shape
        if curr_state == PST_CHARGING:
            charge_bar_y = y + (1 if self.position == "top" else -1)
            display.line(
                int(x - player_half_width),
                charge_bar_y,
                int(x - player_half_width + player_half_width * self.charge_pct),
                charge_bar_y,
                1,
            )
            display.line(
                int(x + player_half_width),
                charge_bar_y,
                int(x + player_half_width - player_half_width * self.charge_pct),
                charge_bar_y,
                1,
            )

        # Draw the projectile
        if self.projectile:
            self.projectile.draw()


class ComputerController:
    def __init__(self, player):
        self.player = player
        self.last_shot_time = None  # Track the last time a projectile was shot

    def play(self):
        current_time = self.player.time.ticks_ms()
        if not self.player.projectile:
            # Check if at least 3 seconds have passed since the last shot
            if (
                self.last_shot_time is None
                or (current_time - self.last_shot_time) >= 3000
            ):
                self.player.play(True)
        else:  # If not in defensive mode, assume offensive mode
            self.last_shot_time = current_time
            self.player.play(False)


class GameLogic(BaseGameLogic):
    def __init__(self, device: GameDevice) -> None:
        self.screen_width = device.display.width
        self.screen_height = device.display.height
        super().__init__(device)

    def load(self):
        print("game loaded")
        self.count_down_to_invert = 0
        self.start_game_tick = self.device.time.ticks_ms()
        self.hit_mode = False
        self.top_player = Player(
            self.device.time,
            self.device.display,
            position="top",
            power_points=PLAYER_BASE_POWER_POINTS,
            initialSpeed=PLAYER_INITIAL_SPEED_PX_F,
        )
        self.bottom_player = Player(
            self.device.time,
            self.device.display,
            position="bottom",
            power_points=PLAYER_BASE_POWER_POINTS,
            initialSpeed=PLAYER_INITIAL_SPEED_PX_F,
        )
        self.npc = ComputerController(self.bottom_player)

    def hit(self, shooter: Player, target: Player):
        if shooter.projectile:
            proj_rect = shooter.projectile.get_hit_rect()
            if target.check_hit(proj_rect):
                target.power_points -= 1
                shooter.projectile = None  # Can't hit again!
                self.hit_mode = True

    def game_tick(self):
        device = self.device
        display = device.display
        time = device.time
        button = device.button

        self.top_player.play(button.value() == 0)
        self.npc.play()

        # Move players if in defensive mode
        self.top_player.move()
        self.bottom_player.move()

        # Check each player projectile (if exists)
        # If it reached the other player edge, and the player currently draw
        # line does not cover that section - the hit player loses a power point
        # background should be in the color of the hit player for this frame
        self.hit(self.top_player, self.bottom_player)
        self.hit(self.bottom_player, self.top_player)

        # Clear display and redraw players
        display.fill(0)

        self.top_player.draw()
        self.bottom_player.draw()

        if self.hit_mode:
            self.hit_mode = False
            self.count_down_to_invert = 5
            display.invert(1)
        elif self.count_down_to_invert > 0:
            self.count_down_to_invert -= 1
            if self.count_down_to_invert == 0:
                display.invert(0)

        # display.text("12", 1, 2, 1)
        # display.text("12", 111, 51, 1)
        display.show()
