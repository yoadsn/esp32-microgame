from difflib import diff_bytes
import random
from game_device import GameDevice
from game_logic import GameLogic

REFRESH_RATE_MS = 33

SHORT_CLICK_THR_MS = 220
SPACE_THR_MS = 1250
SEQUENCE_END_THR_MS = 2500

MENU_CLICK_SHORT_THR_MS = 200
MENU_CLICK_LONG_THR_MS = 990  # based on the refresh rate to allow 1x pixel per frame
MAIN_MENU_TEXT_PAD = 10

MENU_PROGRESS_BAR_WIDTH = 40
MENU_ITEM_EASY = "Easy"
MENU_ITEM_HARD = "Hard"
MENU_ITEM_HOW_TO = "How To"
PROGRESS_BAR_HEIGHT = 5

SOUND_TEXT_ON = "on"
SOUND_TEXT_OFF = "off"

SHORT_SYMBOL = "."
LONG_SYMBOL = "-"
SPACE_SYMBOL = " "

GAME_TIMER_S = 45
EASY_WRONG_POINTS_REDUCTION = 3
HARD_WRONG_POINTS_REDUCTION = 5


class GameRules:
    letters_dict = {
        "A": ".-",
        "B": "-...",
        "C": "-.-.",
        "D": "-..",
        "E": ".",
        "F": "..-.",
        "G": "--.",
        "H": "....",
        "I": "..",
        "J": ".---",
        "K": "-.-",
        "L": ".-..",
        "M": "--",
        "N": "-.",
        "O": "---",
        "P": ".--.",
        "Q": "--.-",
        "R": ".-.",
        "S": "...",
        "T": "-",
        "U": "..-",
        "V": "...-",
        "W": ".--",
        "X": "-..-",
        "Y": "-.--",
        "Z": "--..",
    }
    easy_words = [
        "zap",
        "zip",
        "PTK",
        "jog",
        "CPU",
        "JER",
        "jar",
        "guy",
        "wax",
        "fox",
        "joe",
        "seq",
        "jay",
        "jig",
        "job",
        "fab",
        "bow",
        "tax",
    ]
    hard_words = ["hell", "intel", "cool", "wand", "flip"]
    wrong_code = False
    code_complete = False
    timer_expired = False
    word = ""
    code = []
    points = 0
    difficulty = MENU_ITEM_EASY

    captured_sequence = []
    cur_char_idx = 0

    def __init__(self, difficulty):
        self.wrong_code = False
        self.code_complete = False
        self.timer_expired = False
        self.points = 0
        self.captured_sequence = []
        self.cur_char_idx = 0
        self.difficulty = difficulty

    def gen_new_word(self):

        if self.difficulty == MENU_ITEM_EASY:
            self.word = random.choice(self.easy_words)
        else:
            self.word = random.choice(self.hard_words)

        self.code = self.translate_to_morse(self.word)
        self.wrong_code = False
        self.code_complete = False
        self.timer_expired = False
        self.captured_sequence = []
        self.cur_char_idx = 0

    def translate_to_morse(self, word):
        code = []
        for c in word:
            code.append(self.letters_dict.get(c.upper()))
            code.append(SPACE_SYMBOL)

        return "".join(str(x) for x in code)

    def calculate_code_pixel_count(self, captured):
        x = 0
        if captured:
            code = self.captured_sequence
        else:
            code = self.code
        for c in code:
            if c == SHORT_SYMBOL:
                x += 4
            elif c == LONG_SYMBOL:
                x += 7
            elif c == SPACE_SYMBOL:
                x += 3

        return x

    def is_code_input_started(self):
        if len(self.captured_sequence) > 0:
            return True
        return False

    def is_last_symbol_space(self):
        if len(self.captured_sequence) == 0:
            return False

        if self.captured_sequence[-1] == SPACE_SYMBOL:
            return True

        return False

    def register_code_input(self, symbol):
        self.captured_sequence.append(symbol)
        print(self.captured_sequence)

        if self.code[self.cur_char_idx] == symbol:
            self.cur_char_idx += 1

            if self.difficulty == MENU_ITEM_EASY:
                self.points += 1
            else:
                self.points += 2
            if self.cur_char_idx == len(self.code) - 1:
                self.code_complete = True

        else:
            print("wrong code")
            self.wrong_code = True

    def register_input_timeout(self):
        if self.is_code_input_started():
            print("time out - game over!")
            # self.cur_char_idx = 0
            # self.captured_sequence = []
            self.wrong_code = True

    def add_points_upon_code_complete(self):
        if self.difficulty is MENU_ITEM_EASY:
            self.points += EASY_WRONG_POINTS_REDUCTION
        else:
            self.points += HARD_WRONG_POINTS_REDUCTION

    def reduce_points_upon_wrong_code(self):
        if self.difficulty is MENU_ITEM_EASY:
            self.points -= EASY_WRONG_POINTS_REDUCTION
        else:
            self.points -= HARD_WRONG_POINTS_REDUCTION

        if self.points < 0:
            self.points = 0

    def is_code_completed(self):
        return self.code_complete

    def is_code_wrong(self):
        return self.wrong_code


class LevelState:
    def __init__(self) -> None:
        pass


class MenuState:
    def __init__(self) -> None:
        pass


class MorseGameLogic(GameLogic):
    def __init__(self, device: GameDevice) -> None:
        self.screen_width = device.display.width
        self.screen_height = device.display.height
        super().__init__(device)

    def load(self):
        print("game loaded")
        self.start_game_tick = self.device.time.ticks_ms()
        self.state = "init_menu"

    def game_tick(self):
        device = self.device
        display = device.display
        time = device.time
        button = device.button

        if self.state == "wait_until":
            if time.ticks_ms() > self.wait_until_tick:
                self.wait_until_tick = None
                self.state = self.state_after_wait
            return

        if self.state == "init_menu":
            self.menu_state = MenuState()
            menu_state = self.menu_state
            menu_state.game_sound = True
            # items = ["Easy", "Hard", "How to", "Sound"]
            menu_state.items = [MENU_ITEM_EASY, MENU_ITEM_HARD, MENU_ITEM_HOW_TO]
            menu_state.selector_index = 0
            menu_state.menu_selection_fill_width = 0
            menu_state.start_click = False
            menu_state.start_click_tick = 0
            self.state = "menu_pending"
            return

        if self.state == "menu_pending":
            menu_state = self.menu_state
            if menu_state.menu_selection_fill_width > MENU_PROGRESS_BAR_WIDTH:
                self.state = "menu_selected"
                return

            self.draw_main_menu(
                int(self.screen_width / 2 - 20),
                20,
                menu_state.items,
                menu_state.selector_index,
                menu_state.menu_selection_fill_width,
                menu_state.game_sound,
            )

            if button.value() == 0:
                # check if the button is clicked from previous tick
                if menu_state.start_click:
                    # calculate for how long it was clicked to mark selection in the ui
                    delta = time.ticks_diff(
                        time.ticks_ms(), menu_state.start_click_tick
                    )
                    if delta > SHORT_CLICK_THR_MS:
                        menu_state.menu_selection_fill_width += (
                            MENU_PROGRESS_BAR_WIDTH
                            / (MENU_CLICK_LONG_THR_MS / REFRESH_RATE_MS)
                        ) * 2

                # check if button was actually pressed on this tick
                if not menu_state.start_click:
                    menu_state.start_click_tick = time.ticks_ms()
                    menu_state.start_click = True
            else:
                # check if button was released on this tick and calculate duration
                if menu_state.start_click:
                    delta = time.ticks_diff(
                        time.ticks_ms(), menu_state.start_click_tick
                    )
                    if delta <= SHORT_CLICK_THR_MS:
                        menu_state.selector_index += 1
                        if menu_state.selector_index > len(menu_state.items) - 1:
                            menu_state.selector_index = 0

                    menu_state.start_click = False
                    menu_state.menu_selection_fill_width = 0

            return

        if self.state == "menu_selected":
            menu_state = self.menu_state
            print(menu_state.items[menu_state.selector_index] + " selected")
            difficulty = menu_state.selector_index
            self.rules = GameRules(difficulty)
            self.state = "init_level"
            return

        ge = self.rules

        if self.state == "init_level":
            ge = self.rules
            ge.gen_new_word()
            self.state = "level_active"
            self.level_state = LevelState()

            self.level_state.start_click = False
            self.level_state.start_click_tick = 0
            self.level_state.end_click_tick = 0
            self.level_state.code_pixel_width = ge.calculate_code_pixel_count(False)
            self.level_state.code_x_pos = int(
                (self.screen_width - self.level_state.code_pixel_width) / 2
            )
            if self.level_state.code_x_pos < 5:
                print(ge.word + " code is too long!! regen...")
                self.state = "init_level"
            return

        level_state = self.level_state

        elapsed_sec = int(time.ticks_diff(time.ticks_ms(), self.start_game_tick) / 1000)
        # first, we draw the screen
        self.draw_screen(
            ge, level_state.code_x_pos, level_state.code_pixel_width, elapsed_sec
        )

        # check if we completed the code sequence
        if ge.is_code_completed():
            display.text("CORRECT", 30, 10, 1)
            display.show()
            self.state = "wait_until"
            self.wait_until_tick = time.ticks_ms() + 1000
            self.state_after_wait = "init_level"
            return

        # check if the game timer expired
        if elapsed_sec > GAME_TIMER_S:
            display.text("TIME OUT", 30, 10, 1)
            display.show()
            self.state = "wait_until"
            self.wait_until_tick = time.ticks_ms() + 2000
            self.state_after_wait = "init_menu"
            # should kill the game
            return

        if ge.is_code_wrong():
            display.text("WRONG", 30, 10, 1)
            display.show()
            self.state = "wait_until"
            self.wait_until_tick = time.ticks_ms() + 1000
            self.state_after_wait = "init_level"
            # TODO Here we kill the game OR we reduce points and keep playing until timer ends
            return

        # now, we handle button inputs
        if button.value() == 0:
            # check if button was actually pressed on this tick
            if not level_state.start_click:
                level_state.start_click_tick = time.ticks_ms()
                level_state.start_click = True
        else:
            # check if button was released on this tick and calculate duration
            if level_state.start_click:
                delta = time.ticks_diff(time.ticks_ms(), level_state.start_click_tick)
                if delta <= SHORT_CLICK_THR_MS:
                    ge.register_code_input(SHORT_SYMBOL)
                else:
                    ge.register_code_input(LONG_SYMBOL)

                level_state.start_click = False
                level_state.end_click_tick = time.ticks_ms()
            # else, button is still unpressed from last tick
            else:
                delta = time.ticks_diff(time.ticks_ms(), level_state.end_click_tick)
                if delta > SPACE_THR_MS:
                    if ge.is_code_input_started() and not ge.is_last_symbol_space():
                        ge.register_code_input(SPACE_SYMBOL)

                if delta > SEQUENCE_END_THR_MS:
                    if ge.is_code_input_started():
                        ge.register_input_timeout()
                        # print('game over - timeout!')
                        # TODO game over here!
        return

    def draw_main_menu(
        self, x_pos, y_pos, items, selector_index, menu_selection_fill_width, sound
    ):
        device = self.device
        display = device.display
        sound_text = SOUND_TEXT_ON
        if not sound:
            sound_text = SOUND_TEXT_OFF
        display.fill(0)
        self.draw_frame()

        y = y_pos
        for item in items:
            display.text(item, x_pos, y, 1)
            y += MAIN_MENU_TEXT_PAD

        self.draw_menu_selector(x_pos, y_pos, selector_index)

        display.rect(x_pos, 10, MENU_PROGRESS_BAR_WIDTH, 5, 1)
        display.fill_rect(x_pos, 10, int(menu_selection_fill_width), 5, 1)

        display.show()

    def draw_menu_selector(self, x_pos, y_pos, selector_index):
        device = self.device
        display = device.display
        x = x_pos - 10
        y = y_pos + 1 + selector_index * MAIN_MENU_TEXT_PAD

        display.line(x, y, x + 4, y + 2, 1)
        display.line(x, y, x, y + 4, 1)
        display.line(x, y + 4, x + 4, y + 2, 1)

    def draw_screen(self, ge, code_x_pos, code_pixel_width, elapsed_sec):
        device = self.device
        display = device.display
        ge = self.rules
        display.fill(0)
        self.draw_frame()
        self.draw_points(ge)
        self.draw_timer(elapsed_sec)
        self.draw_word(ge, int(self.screen_height / 2 - 10))
        self.draw_code_pixels(ge, code_x_pos, int(self.screen_height / 2))
        self.draw_progress_bar(
            ge, code_x_pos - 1, int(self.screen_height / 2) + 15, code_pixel_width - 3
        )
        # display.text(seq_string, 30, 10, 1)
        display.show()

    def draw_frame(self):
        device = self.device
        display = device.display
        display.line(0, 0, self.screen_width - 1, 0, 1)
        display.line(0, 0, 0, self.screen_height - 1, 1)
        display.line(
            self.screen_width - 1, 0, self.screen_width - 1, self.screen_height - 1, 1
        )
        display.line(
            0, self.screen_height - 1, self.screen_width - 1, self.screen_height - 1, 1
        )

    def draw_points(self, ge):
        device = self.device
        display = device.display
        ge = self.rules
        display.text("P:{}".format(str(ge.points)), 8, 8, 1)

    def draw_timer(self, elapsed_sec):
        device = self.device
        display = device.display
        display.text(
            "T:{}".format(str(GAME_TIMER_S - elapsed_sec)), self.screen_width - 40, 8, 1
        )

    def draw_word(self, ge, y_pos):
        device = self.device
        display = device.display
        ge = self.rules
        x_pos = int((self.screen_width - len(ge.word) * 10) / 2)
        word_height = 12
        frame_pad = 5
        display.text(ge.word, x_pos, y_pos, 1)

    def draw_code_pixels(
        self,
        ge,
        x,
        y,
    ):
        device = self.device
        display = device.display
        ge = self.rules
        for c in ge.code:
            if c == SHORT_SYMBOL:
                display.fill_rect(x, y + 4, 3, 3, 1)
                x += 4
            elif c == LONG_SYMBOL:
                display.fill_rect(x, y + 4, 6, 3, 1)
                x += 7
            elif c == SPACE_SYMBOL:
                x += 3

    def draw_progress_bar(self, ge, x, y, width):
        device = self.device
        display = device.display
        ge = self.rules
        display.line(x, y, x + width, y, 1)
        display.line(x, y, x, y + PROGRESS_BAR_HEIGHT, 1)
        display.line(x + width, y, x + width, y + PROGRESS_BAR_HEIGHT, 1)
        display.line(x, y + PROGRESS_BAR_HEIGHT, x + width, y + PROGRESS_BAR_HEIGHT, 1)

        fill_width = ge.calculate_code_pixel_count(True)
        display.fill_rect(x + 1, y, fill_width, PROGRESS_BAR_HEIGHT, 1)
