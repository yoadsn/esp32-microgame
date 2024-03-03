import random

import time
from machine import Pin, SoftI2C, RTC
import ssd1306
import _thread as th
from time import sleep_ms

i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=4000000)
display = ssd1306.SSD1306_I2C(128, 64, i2c)  # display object
button = Pin(4, Pin.IN, Pin.PULL_UP)

SCREEN_WIDTH = display.width
SCREEN_HEIGHT = display.height
REFRESH_RATE_MS = 33

SHORT_CLICK_THR_MS = 220
SPACE_THR_MS = 1250
SEQUENCE_END_THR_MS = 2500

MENU_CLICK_SHORT_THR_MS = 200
MENU_CLICK_LONG_THR_MS = 990 #based on the refresh rate to allow 1x pixel per frame
MAIN_MENU_TEXT_PAD = 10

MENU_PROGRESS_BAR_WIDTH = 40
MENU_ITEM_EASY = "Easy"
MENU_ITEM_HARD = "Hard"
MENU_ITEM_HOW_TO = "How To"
PROGRESS_BAR_HEIGHT = 5

SOUND_TEXT_ON = "on"
SOUND_TEXT_OFF = "off"

SHORT_SYMBOL = '.'
LONG_SYMBOL = '-'
SPACE_SYMBOL = ' '

GAME_TIMER_S = 3
EASY_WRONG_POINTS_REDUCTION = 3
HARD_WRONG_POINTS_REDUCTION = 5


class GameEngine:
    letters_dict = {
        'A': '.-',
        'B': '-...',
        'C': '-.-.',
        'D': '-..',
        'E': '.',
        'F': '..-.',
        'G': '--.',
        'H': '....',
        'I': '..',
        'J': '.---',
        'K': '-.-',
        'L': '.-..',
        'M': '--',
        'N': '-.',
        'O': '---',
        'P': '.--.',
        'Q': '--.-',
        'R': '.-.',
        'S': '...',
        'T': '-',
        'U': '..-',
        'V': '...-',
        'W': '.--',
        'X': '-..-',
        'Y': '-.--',
        'Z': '--..',
    }
    easy_words = ["zap", "zip", "PTK", "jog", "CPU", "JER", "jar", "guy", "wax", "fox", "joe", "seq", "jay", "jig",
                  "job", "fab", "bow", "tax"]
    hard_words = ["hello", "intel", "collect", "world", "forward"]
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
            print('wrong code')
            self.wrong_code = True

    def register_input_timeout(self):
        if self.is_code_input_started():
            print('time out - wrong code')
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

    def register_expired_timer(self):
        self.timer_expired = True

    def is_game_over(self):
        return self.timer_expired


def main_menu_loop():
    game_sound = True
    # items = ["Easy", "Hard", "How to", "Sound"]
    items = [MENU_ITEM_EASY, MENU_ITEM_HARD, MENU_ITEM_HOW_TO]
    selector_index = 0
    menu_selection_fill_width = 0

    start_click = False
    start_click_tick = 0

    while True:
        if menu_selection_fill_width > MENU_PROGRESS_BAR_WIDTH:
            menu_selection_fill_width = 0
            print(items[selector_index] + ' selected')

            if items[selector_index] in (MENU_ITEM_EASY, MENU_ITEM_HARD):
                main_game_loop(items[selector_index], game_sound)
                selector_index = 0
                start_click = False
                start_click_tick = 0

        draw_main_menu(int(SCREEN_WIDTH / 2 - 20), 20, items, selector_index, menu_selection_fill_width, game_sound)

        sleep_ms(REFRESH_RATE_MS)

        # now, we handle button inputs
        if button.value() == 0:
            # check if the button is clicked from previous tick
            if start_click:
                # calculate for how long it was clicked to mark selection in the ui
                delta = time.ticks_diff(time.ticks_ms(), start_click_tick)
                if delta > SHORT_CLICK_THR_MS:
                    menu_selection_fill_width += (MENU_PROGRESS_BAR_WIDTH/(MENU_CLICK_LONG_THR_MS/REFRESH_RATE_MS))*2

            # check if button was actually pressed on this tick
            if not start_click:
                start_click_tick = time.ticks_ms()
                start_click = True
        else:
            # check if button was released on this tick and calculate duration
            if start_click:
                delta = time.ticks_diff(time.ticks_ms(), start_click_tick)
                if delta <= SHORT_CLICK_THR_MS:
                    selector_index += 1
                    if selector_index > len(items) - 1:
                        selector_index = 0

                start_click = False
                menu_selection_fill_width = 0


def draw_main_menu(x_pos, y_pos, items, selector_index, menu_selection_fill_width, sound):
    sound_text = SOUND_TEXT_ON
    if not sound:
        sound_text = SOUND_TEXT_OFF
    display.fill(0)
    draw_frame()

    y = y_pos
    for item in items:
        display.text(item, x_pos, y, 1)
        y += MAIN_MENU_TEXT_PAD

    draw_menu_selector(x_pos, y_pos, selector_index)

    display.rect(x_pos, 10, MENU_PROGRESS_BAR_WIDTH, 5, 1)
    display.fill_rect(x_pos, 10, int(menu_selection_fill_width), 5, 1)

    display.show()


def draw_menu_selector(x_pos, y_pos, selector_index):
    x = x_pos - 10
    y = y_pos + 1 + selector_index * MAIN_MENU_TEXT_PAD

    display.line(x, y, x + 4, y + 2, 1)
    display.line(x, y, x, y + 4, 1)
    display.line(x, y + 4, x + 4, y + 2, 1)


def main_game_loop(difficulty, sound_on):
    game_running = True
    start_game_tick = time.ticks_ms()
    ge = GameEngine(difficulty)

    while game_running:

        if ge.is_game_over():
            break

        ge.gen_new_word()
        sleep_ms(400)

        code_pixel_width = ge.calculate_code_pixel_count(False)
        code_x_pos = int((SCREEN_WIDTH - code_pixel_width) / 2)
        if code_x_pos < 5:
            print(ge.word + ' code is too long!! regen...')
            continue

        start_click = False
        start_click_tick = 0
        end_click_tick = 0

        while True:
            elapsed_sec = int(time.ticks_diff(time.ticks_ms(), start_game_tick) / 1000)
            # first, we draw the screen
            draw_screen(ge, code_x_pos, code_pixel_width, elapsed_sec)

            # check if we completed the code sequence
            if ge.is_code_completed():
                display.text("CORRECT", 30, 10, 1)
                ge.add_points_upon_code_complete()
                # TODO Here we need to highlight the points user got
                display.show()
                sleep_ms(1000)
                break

            # check if the game timer expired
            if elapsed_sec > GAME_TIMER_S:
                ge.register_expired_timer()
                display.text("TIME OUT", 30, 10, 1)
                display.show()
                sleep_ms(2000)
                # TODO Here we need to highlight the final points user got
                break

            if ge.is_code_wrong():
                display.text("WRONG", 30, 10, 1)
                ge.reduce_points_upon_wrong_code()
                display.show()
                sleep_ms(1000)
                # display.fill(0)
                # display.show()
                # TODO we need to show points reduction
                break

            # now, we handle button inputs
            if button.value() == 0:
                # check if button was actually pressed on this tick
                if not start_click:
                    start_click_tick = time.ticks_ms()
                    start_click = True
            else:
                # check if button was released on this tick and calculate duration
                if start_click:
                    delta = time.ticks_diff(time.ticks_ms(), start_click_tick)
                    if delta <= SHORT_CLICK_THR_MS:
                        ge.register_code_input(SHORT_SYMBOL)
                    else:
                        ge.register_code_input(LONG_SYMBOL)

                    start_click = False
                    end_click_tick = time.ticks_ms()
                # else, button is still unpressed from last tick
                else:
                    delta = time.ticks_diff(time.ticks_ms(), end_click_tick)
                    if delta > SPACE_THR_MS:
                        if ge.is_code_input_started() and not ge.is_last_symbol_space():
                            ge.register_code_input(SPACE_SYMBOL)

                    if delta > SEQUENCE_END_THR_MS:
                        if ge.is_code_input_started():
                            ge.register_input_timeout()

            sleep_ms(REFRESH_RATE_MS)


def draw_screen(ge, code_x_pos, code_pixel_width, elapsed_sec):
    display.fill(0)
    draw_frame()
    draw_points(ge)
    draw_timer(elapsed_sec)
    draw_word(ge, int(SCREEN_HEIGHT / 2 - 10))
    draw_code_pixels(ge, code_x_pos, int(SCREEN_HEIGHT / 2))
    draw_progress_bar(ge, code_x_pos - 1, int(SCREEN_HEIGHT / 2) + 15, code_pixel_width - 3)
    # display.text(seq_string, 30, 10, 1)
    display.show()


def draw_frame():
    display.line(0, 0, SCREEN_WIDTH-1, 0, 1)
    display.line(0, 0, 0, SCREEN_HEIGHT - 1, 1)
    display.line(SCREEN_WIDTH-1, 0, SCREEN_WIDTH-1, SCREEN_HEIGHT - 1, 1)
    display.line(0, SCREEN_HEIGHT - 1, SCREEN_WIDTH - 1, SCREEN_HEIGHT - 1, 1)


def draw_points(ge):
    display.text("P:{}".format(str(ge.points)), 8, 8, 1)


def draw_timer(elapsed_sec):

    time_left = GAME_TIMER_S - elapsed_sec
    if time_left < 0:
        time_left = 0
    display.text("T:{}".format(str(time_left)), SCREEN_WIDTH - 40, 8, 1)


def draw_word(ge, y_pos):
    x_pos = int((SCREEN_WIDTH - len(ge.word) * 10) / 2)
    word_height = 12
    frame_pad = 5
    display.text(ge.word, x_pos, y_pos, 1)


def draw_code_pixels(ge, x, y,):
    for c in ge.code:
        if c == SHORT_SYMBOL:
            display.fill_rect(x, y + 4, 3, 3, 1)
            x += 4
        elif c == LONG_SYMBOL:
            display.fill_rect(x, y + 4, 6, 3, 1)
            x += 7
        elif c == SPACE_SYMBOL:
            x += 3


def draw_progress_bar(ge, x, y, width):
    display.line(x, y, x + width, y, 1)
    display.line(x, y, x, y + PROGRESS_BAR_HEIGHT, 1)
    display.line(x + width, y, x + width, y + PROGRESS_BAR_HEIGHT, 1)
    display.line(x, y + PROGRESS_BAR_HEIGHT, x + width, y + PROGRESS_BAR_HEIGHT, 1)

    fill_width = ge.calculate_code_pixel_count(True)
    display.fill_rect(x + 1, y, fill_width, PROGRESS_BAR_HEIGHT, 1)


main_menu_loop()
