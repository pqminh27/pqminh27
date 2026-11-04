#!/usr/bin/env python3
"""Write clean dark and light SVG variants of a generated contribution snake."""

import sys
from pathlib import Path


COLORS = {
    "#161b22": "#ebedf0",
    "#0e4429": "#9be9a8",
    "#006d32": "#40c463",
    "#26a641": "#30a14e",
    "#39d353": "#216e39",
    "#b7ffd0": "#0d532a",
    "#8affc1": "#1a7f37",
    "#7d8590": "#57606a",
    "#0d1117": "#ffffff",
    "#30363d": "#d0d7de",
}


def clean_svg(svg: str) -> str:
    return "\n".join(line.rstrip() for line in svg.splitlines()) + "\n"


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: prepare_snake.py INPUT.svg DARK_OUTPUT.svg LIGHT_OUTPUT.svg"
        )

    source = Path(sys.argv[1])
    dark_output = Path(sys.argv[2])
    light_output = Path(sys.argv[3])
    dark_svg = clean_svg(source.read_text(encoding="utf-8"))
    light_svg = dark_svg
    for dark, light in COLORS.items():
        light_svg = light_svg.replace(dark, light)

    dark_output.parent.mkdir(parents=True, exist_ok=True)
    light_output.parent.mkdir(parents=True, exist_ok=True)
    dark_output.write_text(dark_svg, encoding="utf-8")
    light_output.write_text(light_svg, encoding="utf-8")


if __name__ == "__main__":
    main()
