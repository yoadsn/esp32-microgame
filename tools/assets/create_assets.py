import pathlib
import os
from PIL import Image

root_dir = os.path.dirname(os.path.realpath(__file__))
asset_input_dir = pathlib.Path(root_dir) / "assets_in"
asset_output_dir = pathlib.Path(root_dir) / "assets_out"

if not asset_input_dir.exists():
    raise Exception("Input folder missing")

# Create output directory if does not exist
if not asset_output_dir.exists():
    asset_output_dir.mkdir()

for ship_asset in [
    "banner",
    "ship-hull",
    "ship-wingtip",
    "ship-wing-ext",
]:
    # Sprite generation
    with Image.open(asset_input_dir / f"{ship_asset}.png") as im:
        im.convert("1").save(asset_output_dir / f"{ship_asset}.pbm")

for ufo_asset in [
    "ufo-shield",
    "ufo-rapid-fire",
    "ufo-slowdown",
    "ufo-bomb",
    "ufo-powerup",
]:
    # Sprite generation
    with Image.open(asset_input_dir / f"{ufo_asset}.png") as im:
        im.convert("1").save(asset_output_dir / f"{ufo_asset}.pbm")
