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
