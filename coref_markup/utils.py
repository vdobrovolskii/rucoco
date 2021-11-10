import colorsys
from typing import *


COLORS = [
    "#fb8072",
    "#fdb462",
    "#ffed6f",
    "#ffffb3",
    "#ccebc5",
    "#b3de69",
    "#72af79",
    "#a6cee3",
    "#80b1d3",
    "#cab2d6",
    "#bc80bd",
    "#fb9a99",
    "#e2844e",
    "#cacaca"
]

DARK_COLORS = [
    "#e31a1c",
    "#ff7f00",
    "#fdbf6f",
    "#ffdd24",
    "#ffff99",
    "#b2df8a",
    "#33a02c",
    "#a6cee3",
    "#1f78b4",
    "#cab2d6",
    "#6a3d9a",
    "#fb9a99",
    "#b15928"
]

HUE_STEPS = 16


def get_colors(dark_mode: bool) -> Iterable[str]:
    yield from DARK_COLORS if dark_mode else COLORS

    hue_steps = [1 / HUE_STEPS * i for i in range(HUE_STEPS)]
    sat_steps = [0.8, 0.6, 0.4]
    val_steps = [0.8, 0.6, 0.4]

    for s in sat_steps:
        for v in val_steps:
            for h in hue_steps:
                rgb = colorsys.hsv_to_rgb(h, s, v)
                yield ("#" + "{:02x}" * 3).format(*(int(0xff * value) for value in rgb))


def multiply_color(rgb: str, factor: float) -> str:
    values = (int(value, base=16) for value in (rgb[1:3], rgb[3:5], rgb[5:7]))
    values = (int(factor * value) for value in values)
    values = (min(255, value) for value in values)
    return ("#" + "{:02x}" * 3).format(*values)
