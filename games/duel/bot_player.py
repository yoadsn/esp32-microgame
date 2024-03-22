from games.duel.missile import BASE_MISSILE_SPEED, DEFAULT_MISSILE_BLAST_RADIUS
from games.duel.player import PST_STOPPED, Player
from games.duel.ufos import Ufo, UfoTypes, UFO_TYPES_COUNT

_STATE_IDLE = 0
_STATE_SHOOTING = 1
_STATE_EVADING = 2

_MAX_IDLE_TIME_MS = 2500


class BotSkillLevels:
    JOKE = 0
    EASY = 1
    NORMAL = 2
    HARD = 3
    INSANE = 4


BOT_SKILL_LEVEL_NAMES = {
    0: "Joke",
    1: "Easy",
    2: "Normal",
    3: "Hard",
    4: "Insane",
}

MAX_BOT_SKILL_LEVEL = BotSkillLevels.INSANE

_SKILL_LEVELS = [
    # vision inaccuracy (pixel offset), response time (ms until changing to a state), ufo_perplexity (1 - none, 3 - max)
    (10, 1200, 3),  # easy
    (10, 500, 2),  # ok
    (2, 300, 1),  # medium
    (2, 200, 1),  # hard
    (0, 0, 1),  # insane
]


class ComputerController:
    def __init__(
        self,
        field_start: int,
        field_end: int,
        player: Player,
        other_player: Player,
        level: int,  # 0-4
    ):
        self.field_start = field_start
        self.field_end = field_end
        self.field_width = field_end - field_start
        self.player = player
        self.time = self.player.time
        self.other_player = other_player
        self.last_shot_time = 0  # Track the last time a projectile was shot
        self.state = _STATE_IDLE
        self.state_start_time_ms = self.player.time.ticks_ms()
        self.next_state_after_response_time = None
        self.response_time_started_at = _STATE_IDLE
        vision_inaccuracy, response_time, ufo_perplexity = _SKILL_LEVELS[level]
        self.vision_inaccuracy = vision_inaccuracy
        self.response_time = response_time
        self.base_ufo_perplexity = ufo_perplexity
        self.current_ufo_perplexity_offset = ufo_perplexity - 1

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
            + self.vision_inaccuracy
        ) % field_width
        if abs(self_player.x - target_x_at_hit_time) < precision:
            return True
        return False

    def update_dynamic_skills(self):
        # setup a new perplexity offset upcoming detections
        self.current_ufo_perplexity_offset = (  # 0 and up
            int(self.time.ticks_ms()) % self.base_ufo_perplexity
        )
        # switch inaccuracy direction one every shot is fired
        self.vision_inaccuracy = self.vision_inaccuracy * -1

    def is_ufo_type(self, compare_type, to_type):
        if compare_type is None:
            return False
        return (
            compare_type
            == (to_type + self.current_ufo_perplexity_offset) % UFO_TYPES_COUNT
        )

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

        # Only perform state changes if not waiting for the response time to end
        if self.next_state_after_response_time is None:
            if current_state == _STATE_IDLE:
                # Under threat?
                if other_player.missile and not self.is_ufo_type(
                    self_ufo_type, UfoTypes.SHIELD
                ):
                    next_state = _STATE_EVADING
                elif (
                    self.time.ticks_diff(current_time, self.state_start_time_ms)
                    > _MAX_IDLE_TIME_MS
                ):
                    next_state = _STATE_SHOOTING
                elif self.check_on_target(
                    other_player.x - other_player.player_width // 2,
                    other_player.y,
                    0 if other_player.play_state == PST_STOPPED else other_player.vx,
                    precision=6,
                ):
                    next_state = _STATE_SHOOTING
                else:
                    for ufo in ufos:
                        if (
                            self.is_ufo_type(ufo.type, UfoTypes.POWER)
                            or self.is_ufo_type(ufo.type, UfoTypes.RAPID_FIRE)
                            or self.is_ufo_type(ufo.type, UfoTypes.SHIELD)
                        ):
                            if self.check_on_target(
                                ufo.x, ufo.y, ufo.speed * ufo.direction_x
                            ):
                                next_state = _STATE_SHOOTING
                                break

            elif current_state == _STATE_SHOOTING:
                if self_player.missile:  # after a shot - release
                    # unless - have a rpaid fire UFO
                    if not self.is_ufo_type(self_ufo_type, UfoTypes.RAPID_FIRE):
                        # after every shot - update dynamic skills
                        self.update_dynamic_skills()
                        next_state = _STATE_IDLE
                elif other_player.missile:
                    time_since_last_shot = self.time.ticks_diff(
                        current_time, self.last_shot_time
                    )
                    # Give up and evade if we recently had a shot at the player
                    if time_since_last_shot < 1500:
                        next_state = _STATE_EVADING
            elif current_state == _STATE_EVADING:
                if (
                    # no longer a threat
                    not other_player.missile
                ):
                    next_state = _STATE_IDLE

        # If response time is non zero for this controller
        if self.response_time > 0:
            # if actively waiting for response time to end
            if self.next_state_after_response_time is not None:
                # if the wait time has passed
                if (
                    self.player.time.ticks_diff(
                        current_time, self.response_time_started_at
                    )
                    > self.response_time
                ):
                    next_state = self.next_state_after_response_time
                    self.next_state_after_response_time = None
            # Not waiting - but should wait?
            else:
                # if a transition is expected
                if current_state != next_state:
                    # store the next state we need to get to
                    self.next_state_after_response_time = next_state
                    # keep current state
                    next_state = current_state
                    # when did we start waiting?
                    self.response_time_started_at = current_time

        if current_state != next_state:
            self.state_start_time_ms = current_time

        self.state = current_state = next_state

        played = False
        if current_state == _STATE_SHOOTING:
            played = True
            self_player.play(True)
        elif current_state == _STATE_EVADING:
            if other_player.missile:
                other_player_missile_x = other_player.missile.x + self.vision_inaccuracy
                if (
                    other_player_missile_x < self_start_hit_x
                    or other_player_missile_x > self_end_hit_x
                ):  # safe distance - stay put
                    played = True
                    self_player.play(True)  # stop

        if not played:
            self_player.play(True)
