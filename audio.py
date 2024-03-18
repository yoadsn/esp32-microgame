from hardware.esp32.game_engine import PwmGameAudio

p = PwmGameAudio()

pause = (0, 0, 1)
a = p.load_melody([(3, 5, 1),(3, 6, 1)])

p.play(a)
