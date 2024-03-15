b_whitespace = b"\x20\x09\x0a\x0b\x0c\x0d"


def load_sprite_bytes(filename: str) -> bytearray:
    with open(filename, "rb", buffering=0) as f:
        state = "init"
        width_str = b""
        height_str = b""
        parsing = True
        error = False
        while parsing:
            if state == "init":
                magic = b""
                d = f.read(2)
                magic += d
                if magic != b"P4":
                    error = True
                if f.read(1) in b_whitespace:
                    state = "width"
                else:
                    error = True
            elif state == "width":
                b = f.read(1)
                if b not in b_whitespace:
                    width_str += b
                else:
                    state = "height"
            elif state == "height":
                b = f.read(1)
                if b not in b_whitespace:
                    height_str += b
                else:
                    state = "data"
            elif state == "data":
                img_data = bytearray(f.read())
                parsing = False

    if error:
        raise Exception("Bad File Format")

    img_w = int(width_str)
    img_h = int(height_str)
    return (img_data, img_w, img_h)


def flip_sprite_bytes(
    sprite_bytes: bytearray, w: int, h: int, flip_h: bool = False, flip_v: bool = False
):
    if flip_h or flip_v:
        # restructure as an array of boolean for direct-per-pixel manipulation
        # in the process remove extra bits that were needed to fill last-line-bytes
        packed_length = len(sprite_bytes)
        packed_row_bytes = (w + 7) // 8
        bitmap_array = list(bytearray(w * h))  # pixel per byte - unpacked
        for from_x in range(0, w):
            for from_y in range(0, h):
                packed_byte_idx = from_y * packed_row_bytes + from_x // 8
                packed_bit_idx = from_x % 8
                unpacked_byte_idx = from_y * w + from_x
                packed_bit_location = 8 - packed_bit_idx - 1  # MONO_HLSB
                bitmap_array[unpacked_byte_idx] = (
                    sprite_bytes[packed_byte_idx] >> packed_bit_location & 1
                )

        if flip_v:
            # go over all cols - reverse row order
            for x in range(0, w):
                for y in range(0, h // 2):
                    swap_pixel = y * w + x
                    with_pixel = (h - y - 1) * w + x
                    tmp_val = bitmap_array[swap_pixel]
                    bitmap_array[swap_pixel] = bitmap_array[with_pixel]
                    bitmap_array[with_pixel] = tmp_val

        if flip_h:
            # go over all rows - reverse col order
            for y in range(0, h):
                for x in range(0, w // 2):
                    swap_pixel = y * w + x
                    with_pixel = y * w + (w - x - 1)
                    tmp_val = bitmap_array[swap_pixel]
                    bitmap_array[swap_pixel] = bitmap_array[with_pixel]
                    bitmap_array[with_pixel] = tmp_val

        # pack back per-pixel array to byte array
        flipped_ba = bytearray(packed_length)
        for from_x in range(0, w):
            for from_y in range(0, h):
                packed_byte_idx = from_y * packed_row_bytes + from_x // 8
                packed_bit_idx = from_x % 8
                unpacked_byte_idx = from_y * w + from_x
                packed_bit_location = 8 - packed_bit_idx - 1  # MONO_HLSB
                flipped_ba[packed_byte_idx] |= (
                    bitmap_array[unpacked_byte_idx] << packed_bit_location
                )

        return flipped_ba
    return sprite_bytes


class GameDisplay:
    def show(self):
        pass

    def fill(self, col):
        pass

    def center_text(self, string, col):
        pass

    def text(self, string, x, y, col=1):
        pass

    def line(self, start_pos_x, start_pos_y, end_pos_x, end_pos_y, col):
        pass

    def fill_rect(self, x, y, w, h, col):
        pass

    def rect(self, x, y, w, h, col):
        pass

    def pixel(self, x, y, col):
        pass

    def get_buffer(self, data_ba, w, h):
        pass

    def blit(self, buf, x, y):
        pass

    def blit_onto(self, buf_src, buf_dest, x, y):
        pass


class GameDisplayAsset:
    def __init__(self, buffer, w, h) -> None:
        self.buffer = buffer
        self.w = w
        self.h = h


class GameTime:
    def sleep_ms(self, ms):
        pass

    def ticks_ms(self):
        pass

    def ticks_diff(self, a, b):
        pass

    def tick(self, fps):
        pass


class GameButton:
    def __init__(self) -> None:
        pass

    def value(self):
        pass


class GameSound:
    def __init__(self) -> None:
        pass


class GameAudio:
    def __init__(self) -> None:
        pass

    def play(self, sound_id, interruptable):
        pass

    def load_melody(self, melody):
        pass

    def note_to_freq(self, octave: int, note_idx: int) -> int:
        if octave == 0:
            return 0
        # Distance of C from A in the equal-tempered scale
        distance_from_a = note_idx - 9

        # Adjusting for the octave
        n = (octave - 4) * 12 + distance_from_a

        # Calculate the frequency
        freq = 440 * (2 ** (n / 12))

        # Return the frequency rounded to the nearest whole number
        return round(freq)


class GameDevice:
    def __init__(
        self, time: GameTime, display: GameDisplay, button: GameButton, audio: GameAudio
    ) -> None:
        self.time = time
        self.display = display
        self.button = button
        self.audio = audio

    def load_display_asset(
        self, filename: str, flip_h: bool = False, flip_v: bool = False
    ) -> GameDisplayAsset:
        (ba, w, h) = load_sprite_bytes(filename)
        sprite_bytes = flip_sprite_bytes(ba, w, h, flip_h=flip_h, flip_v=flip_v)

        return GameDisplayAsset(self.display.get_buffer(sprite_bytes, w, h), w, h)
