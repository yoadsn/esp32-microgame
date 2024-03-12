import random
from game_device import GameDevice
from game_logic import BaseGameLogic


class Projectile:
    def __init__(self, x, y, direction):
        self.x = x
        self.y = y
        self.direction = direction  # 1 for downwards, -1 for upwards

    def move(self):
        self.y += self.direction  # Move the projectile 1 pixel per 5 frames

    def draw(self, display):
        display.pixel(int(self.x), int(self.y), 1)

class Player:
    def __init__(self, power_points=20, position="top", color=1, initialSpeed=4):
        self.power_points = power_points
        self.position = position
        self.color = color
        self.mode = "defensive"
        self.x = 0
        self.vx = initialSpeed
        self.building_cannon = False
        self.reverting_to_defensive = False
        self.cannon_height = 0
        self.projectile = None

    def move(self, width, height):
        if self.mode == "defensive" and not self.building_cannon:
            # Normal defensive movement logic
            self.x += self.vx
            if self.x <= 0 or self.x + self.power_points >= width:
                self.vx *= -1
                self.x = max(self.x, 0)

        if (
            self.mode == "offensive"
            and not self.building_cannon
            and not self.reverting_to_defensive
            and not self.projectile
        ):
            self.building_cannon = True
        elif self.building_cannon and not self.reverting_to_defensive:
            # Building cannon logic
            if self.cannon_height < self.power_points:
                self.cannon_height += 0.8  # Build the cannon by 1 pixel every 10 frames
            else:
                # Cannon complete, shoot projectile
                midpoint = self.x + self.power_points // 2
                direction = 1 if self.position == "top" else -1
                self.projectile = Projectile(
                    midpoint,
                    1 if self.position == "top" else height - 2,
                    direction,
                )
                self.power_points -= 1  # Lose one power point after shooting
                self.building_cannon = False  # Reset cannon building
                self.cannon_height = 0  # Reset cannon height
        elif self.reverting_to_defensive and self.cannon_height > 0:
            self.cannon_height -= 1  # Dismantle the cannon if reverting to defensive
            if self.cannon_height == 0:
                self.reverting_to_defensive = False  # Reset flag once fully reverted

        # Move projectile if it exists
        if self.projectile:
            self.projectile.move()
            if self.projectile.y <= 0 or self.projectile.y >= height:
                self.projectile = None  # Remove projectile when it leaves the screen

        # Reset building cannon and reverting to defensive states if projectile is shot
        if self.projectile and self.cannon_height > 0:
            self.building_cannon = False
            self.reverting_to_defensive = False
            self.cannon_height = 0

    def draw(self, display):
        y = 1 if self.position == "top" else display.height - 2
        if not self.building_cannon:
            # Draw player as a horizontal line
            for i in range(self.power_points):
                display.pixel(int(self.x) + i, y, self.color)
        else:
            # Draw the cannon shape
            midpoint = self.x + self.power_points // 2
            player_length = self.power_points - int(self.cannon_height)
            for i in range(player_length):
                display.pixel(int(midpoint - player_length // 2) + i, y, self.color)

            for i in range(int(min(self.cannon_height, 5))):
                display.pixel(
                    midpoint,
                    (y + i if self.position == "top" else y - i),
                    self.color,
                )

        # Draw the projectile
        if self.projectile:
            self.projectile.draw(display)


class ComputerController:
    def __init__(self, player):
        self.player = player
        self.last_shot_time = None  # Track the last time a projectile was shot

    def play(self, time):
        current_time = time.ticks_ms()
        if self.player.mode == "defensive":
            # Check if at least 3 seconds have passed since the last shot
            if (
                self.last_shot_time is None
                or (current_time - self.last_shot_time) >= 3000
            ):
                self.player.mode = "offensive"
        else:  # If not in defensive mode, assume offensive mode
            # Once a projectile is shot, update last_shot_time and revert to defensive mode
            if self.player.projectile is not None:
                self.last_shot_time = current_time
                self.player.mode = "defensive"


class GameLogic(BaseGameLogic):
    def __init__(self, device: GameDevice) -> None:
        self.screen_width = device.display.width
        self.screen_height = device.display.height
        super().__init__(device)

    def load(self):
        print("game loaded")
        self.count_down_to_invert = 0
        self.start_game_tick = self.device.time.ticks_ms()
        self.top_player = Player(position="top", color=1, power_points=40)
        self.bottom_player = Player(
            position="bottom", color=1, power_points=40
        )
        self.npc = ComputerController(self.bottom_player)

    def game_tick(self):
        device = self.device
        display = device.display
        time = device.time
        button = device.button

        # Update player modes based on human input
        self.top_player.mode = "offensive" if button.value() == 0 else "defensive"

        self.npc.play(time)

        # Move players if in defensive mode
        self.top_player.move(display.width, display.height)
        self.bottom_player.move(display.width, display.height)

        # Check each player projectile (if exists)
        # If it reached the other player edge, and the player currently draw
        # line does not cover that section - the hit player loses a power point
        # background should be in the color of the hit player for this frame
        invert_mode = False
        if self.top_player.projectile:
            if self.top_player.projectile.y >= display.height - 2:
                if (
                    self.bottom_player.x
                    <= self.top_player.projectile.x
                    <= self.bottom_player.x + self.bottom_player.power_points
                ):
                    self.bottom_player.power_points -= (
                        1  # Computer player loses a power point
                    )
                    invert_mode = True

        # Check for computer player's projectile hitting the human player
        if self.bottom_player.projectile:
            if (
                self.bottom_player.projectile.y <= 1
            ):  # Again, adjust according to your projectile logic
                if (
                    self.top_player.x
                    <= self.bottom_player.projectile.x
                    <= self.top_player.x + self.top_player.power_points
                ):
                    self.top_player.power_points -= (
                        1  # Human player loses a power point
                    )
                    invert_mode = True

        # Clear display and redraw players
        display.fill(0)
        self.top_player.draw(display)
        self.bottom_player.draw(display)

        if invert_mode:
            self.count_down_to_invert = 5
            display.invert(1)
        elif self.count_down_to_invert > 0:
            self.count_down_to_invert -= 1
            if self.count_down_to_invert == 0:
                display.invert(0)

        fbuf = framebuf.FrameBuffer(data, 128, 64, framebuf.MONO_HLSB)

        display.text("12", 1, 2, 1)
        display.text("12", 111, 51, 1)
        display.show()
        
