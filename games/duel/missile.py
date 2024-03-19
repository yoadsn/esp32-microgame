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
        base_x = int(self.x)
        base_y = int(self.y)
        self.display.line(base_x - 1, base_y, base_x, base_y, 1)

    def get_hit_rect(self):
        return (
            self.x - self.blast_radius,
            self.y - self.blast_radius,
            self.x + self.blast_radius,
            self.y + self.blast_radius,
        )
