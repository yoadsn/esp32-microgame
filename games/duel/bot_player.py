from games.duel.player import Player


class ComputerController:
    def __init__(self, player: Player):
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
