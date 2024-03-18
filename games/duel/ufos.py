from random import random
from math import sin, pi
from game_device import GameDevice


class UfoTypes:
    SHIELD = 0
    RAPID_FIRE = 1
    DAMAGE = 2
    FROZEN = 3


# Probs are relative to the total probs on all types
UFO_CONFIG_PROB = 0
UFO_CONFIG_SPEED = 1
UFO_CONFIG_TTL = 2
UFO_TYPES_CONFIG = [
    # prob, speed, ttl
    (1, 0.6, 4000),  # shield
    (4, 1.2, 5000),  # rapid fire
    (2, 0.4, 0),  # damage
    (4, 0.4, 3000),  # frozen
]

UFO_TOTAL_PROBS = sum(prob for (prob, speed, ttl) in UFO_TYPES_CONFIG)
UFO_TYPES_CUMM_PROBS = []
prob_so_far = 0
for tp in range(0, len(UFO_TYPES_CONFIG)):
    this_type_abs_prob = UFO_TYPES_CONFIG[tp][UFO_CONFIG_PROB]
    this_type_prob = this_type_abs_prob / UFO_TOTAL_PROBS
    prob_so_far += this_type_prob
    UFO_TYPES_CUMM_PROBS.append((tp, prob_so_far))


def get_random_ufo_type():
    r = random()
    for tp in UFO_TYPES_CUMM_PROBS:
        if r <= tp[1]:
            return tp[0]


class Ufo:
    def __init__(
        self,
        device: GameDevice,
        field_start_x,
        field_end_x,
        y,
        type: int = UfoTypes.SHIELD,
        direction_x=0,
    ):
        self.display = device.display
        self.time = device.time
        self.y = y
        self.type = type
        self.direction_x = direction_x
        self.speed = UFO_TYPES_CONFIG[type][UFO_CONFIG_SPEED]
        self.base_y = self.y
        self.width = 8
        self.height = 8
        self.half_w = self.width // 2
        self.half_h = self.height // 2
        self.x = field_start_x if direction_x == 1 else field_end_x - self.width
        self.captured = False
        self.captured_at_ticks_ms: int = 0
        self.time_to_live_ms: int = UFO_TYPES_CONFIG[type][UFO_CONFIG_TTL]
        self.dead = False

    def move(self):
        if self.captured:
            capture_time_ms = self.time.ticks_diff(
                self.time.ticks_ms(), self.captured_at_ticks_ms
            )
            if capture_time_ms > self.time_to_live_ms:
                self.dead = True
        else:
            self.x += self.direction_x * self.speed

            # Add a wobble effect around main trajectory
            self.y = self.base_y + sin(self.x / 20 * pi * 2) * 5

    def draw(
        self,
        prison_start_x: int = None,
        prison_start_y: int = None,
        prison_end_x: int = None,
        prison_end_y: int = None,
    ):
        if not self.dead:
            if self.captured:
                center_x = (prison_end_x + prison_start_x) // 2
                center_y = (prison_end_y + prison_start_y) // 2
                self.display.text(
                    f"{self.type}", center_x - self.half_w, center_y - self.half_h
                )
            else:
                # TEMP - no. instead of icon
                self.display.text(f"{self.type}", int(self.x), int(self.y))

    def check_hit(self, hit_rect):
        if not self.dead:
            x1, y1, x2, y2 = hit_rect
            ufo_y1 = self.y
            # Why the ugly nested if? To save on calcs
            if y2 >= ufo_y1:
                ufo_y2 = self.y + self.width
                if y1 <= ufo_y2:
                    ufo_x1 = self.x - self.half_w
                    if x2 >= ufo_x1:
                        ufo_x2 = self.x + self.half_w
                        if x1 <= ufo_x2:
                            return True
        return False

    def set_captured(self):
        self.captured_at_ticks_ms = self.time.ticks_ms()
        self.captured = True

    def is_cpatured(self):
        return self.captured
