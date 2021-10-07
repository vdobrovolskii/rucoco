import colorsys
from typing import *


HUE_STEPS = 16


def get_colors() -> Iterable[str]:
    hue_steps = [1 / HUE_STEPS * i for i in range(HUE_STEPS)]
    sat_steps = [0.8, 0.6, 0.4]
    val_steps = [0.8, 0.6, 0.4]

    for s in sat_steps:
        for v in val_steps:
            for h in hue_steps:
                rgb = colorsys.hsv_to_rgb(h, s, v)
                yield ("#" + "{:02x}" * 3).format(*(int(0xff * value) for value in rgb))


def get_shade(rgb: str, factor: float) -> str:
    values = (int(value, base=16) for value in (rgb[1:3], rgb[3:5], rgb[5:7]))
    return ("#" + "{:02x}" * 3).format(*(int(factor * value) for value in values))
