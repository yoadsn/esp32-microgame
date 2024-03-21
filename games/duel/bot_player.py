from games.duel.missile import BASE_MISSILE_SPEED, DEFAULT_MISSILE_BLAST_RADIUS
from games.duel.player import PST_DEFENSIVE, Player
from games.duel.ufos import Ufo, UfoTypes

_STATE_IDLE = 0
_STATE_SHOOTING = 1
_STATE_EVADING = 2

_MAX_IDLE_TIME_MS = 2500


class ComputerController:
    def __init__(
        self, field_start: int, field_end: int, player: Player, other_player: Player
    ):
        self.field_start = field_start
        self.field_end = field_end
        self.field_width = field_end - field_start
        self.player = player
        self.other_player = other_player
        self.last_shot_time = None  # Track the last time a projectile was shot
        self.state = _STATE_IDLE
        self.state_start_time_ms = self.player.time.ticks_ms()

    def check_on_target(self, target_x, target_y, target_velocity, precision=2):
        self_player = self.player
        field_width = self.field_width
        height_to_target_y = abs(target_y - self_player.y)
        missile_flight_time = (
            height_to_target_y / BASE_MISSILE_SPEED  # missile travel speed
        )
        charge_time = self_player.charge_time_ticks
        target_x_at_hit_time = (
            target_x
            + (target_velocity) * (missile_flight_time + charge_time)
            + field_width
        ) % field_width
        if abs(self_player.x - target_x_at_hit_time) < precision:
            return True
        return False

    def play(self, ufos: list[Ufo]):
        current_time = self.player.time.ticks_ms()
        self_player = self.player
        self_x = self_player.x
        self_half_hit_width = (
            self_player.player_width // 2 + DEFAULT_MISSILE_BLAST_RADIUS
        )
        self_ufo_type = None if not self_player.ufo else self_player.ufo.type
        self_start_hit_x = self_x - self_half_hit_width
        self_end_hit_x = self_x + self_half_hit_width
        other_player = self.other_player
        current_state = self.state
        next_state = current_state

        if current_state == _STATE_IDLE:
            # Under threat?
            if other_player.missile and self_ufo_type != UfoTypes.SHIELD:
                next_state = _STATE_EVADING
            elif (
                self.player.time.ticks_diff(current_time, self.state_start_time_ms)
                > _MAX_IDLE_TIME_MS
            ):
                next_state = _STATE_SHOOTING
            elif self.check_on_target(
                other_player.x - other_player.player_width // 2,
                other_player.y,
                0 if other_player.play_state == PST_DEFENSIVE else other_player.vx,
                precision=6,
            ):
                next_state = _STATE_SHOOTING
            else:
                for ufo in ufos:
                    if ufo.type in [
                        UfoTypes.POWER,
                        UfoTypes.RAPID_FIRE,
                        UfoTypes.SHIELD,
                    ]:
                        if self.check_on_target(
                            ufo.x, ufo.y, ufo.speed * ufo.direction_x
                        ):
                            next_state = _STATE_SHOOTING
                            break

        elif current_state == _STATE_SHOOTING:
            if self_player.missile:  # after a shot - release
                # unless - have a rpaid fire UFO
                if self_ufo_type != UfoTypes.RAPID_FIRE:
                    next_state = _STATE_IDLE
            elif other_player.missile:
                next_state = _STATE_EVADING
        elif current_state == _STATE_EVADING:
            if (
                # no longer a threat
                not other_player.missile
            ):
                next_state = _STATE_IDLE

        if current_state != next_state:
            self.state_start_time_ms = current_time

        self.state = current_state = next_state

        played = False
        if current_state == _STATE_SHOOTING:
            if not self_player.missile:  # wait until can shoot
                played = True
                self_player.play(True)
        elif current_state == _STATE_EVADING:
            if other_player.missile and (
                other_player.missile.x < self_start_hit_x
                or other_player.missile.x > self_end_hit_x
            ):  # safe distance - stay put
                played = True
                self_player.play(True)  # stop

        if not played:
            self_player.play(False)
