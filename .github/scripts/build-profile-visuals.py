#!/usr/bin/env python3
"""Split the upstream profile SVG into a contribution hero and clean summaries."""

from __future__ import annotations

import copy
import re
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "profile-3d-contrib"
SOURCE = ASSETS / "profile-night-view.svg"
SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)


def tag(name: str) -> str:
    return f"{{{SVG_NS}}}{name}"


def set_text(
    parent: ET.Element,
    content: str,
    *,
    x: int,
    y: int,
    size: int,
    color: str,
    weight: int = 400,
    anchor: str = "start",
) -> ET.Element:
    element = ET.SubElement(
        parent,
        tag("text"),
        {
            "x": str(x),
            "y": str(y),
            "font-size": str(size),
            "font-weight": str(weight),
            "text-anchor": anchor,
            "fill": color,
        },
    )
    element.text = content
    return element


def svg_root(width: int, height: int) -> ET.Element:
    return ET.Element(
        tag("svg"),
        {
            "width": str(width),
            "height": str(height),
            "viewBox": f"0 0 {width} {height}",
            "role": "img",
        },
    )


def write_svg(path: Path, root: ET.Element) -> None:
    ET.indent(root, space="  ")
    path.write_bytes(ET.tostring(root, encoding="utf-8", xml_declaration=True))


def read_source() -> tuple[
    ET.Element, ET.Element, ET.Element, ET.Element, ET.Element
]:
    root = ET.parse(SOURCE).getroot()
    groups = [child for child in root if child.tag == tag("g")]

    grid = max(
        groups,
        key=lambda group: sum(1 for element in group.iter(tag("rect"))),
    )
    radar_labels = {"Commit", "Issue", "PullReq", "Review", "Repo"}
    radar = next(
        (
            group
            for group in groups
            if radar_labels.issubset(
                {
                    (element.text or "").strip()
                    for element in group.iter(tag("text"))
                }
            )
        ),
        None,
    )
    language_labels = {"Python", "Rust", "TypeScript", "HTML", "JavaScript"}
    language_panel = next(
        (
            group
            for group in groups
            if language_labels.issubset(
                {
                    (element.text or "").strip()
                    for element in group.iter(tag("text"))
                }
            )
        ),
        None,
    )
    footer = next(
        (
            group
            for group in groups
            if any(
                (element.text or "").strip() == "contributions"
                for element in group.iter(tag("text"))
            )
        ),
        None,
    )
    if radar is None or language_panel is None or footer is None:
        raise RuntimeError(f"Could not locate all panels in {SOURCE}")

    return root, grid, radar, language_panel, footer


def read_activity(radar: ET.Element) -> list[tuple[str, int]]:
    labels = {
        "Commit": "Commits",
        "Issue": "Issues",
        "PullReq": "Pull requests",
        "Review": "Reviews",
        "Repo": "Repository contributions",
    }
    values: dict[str, int] = {}
    for element in radar.iter(tag("text")):
        label = (element.text or "").strip()
        title = element.find(tag("title"))
        if label in labels and title is not None and title.text is not None:
            values[label] = int(title.text)
    if set(values) != set(labels):
        raise RuntimeError("Could not read all contribution counts from radar")
    return [(labels[label], values[label]) for label in labels]


def read_languages(panel: ET.Element) -> list[tuple[str, int, str]]:
    languages: list[tuple[str, int, str]] = []
    for element in panel.iter(tag("path")):
        title = element.find(tag("title"))
        if title is None or not title.text:
            continue
        match = re.fullmatch(r"(.+?)\s+(\d+)", title.text.strip())
        if match is None:
            continue
        style = element.get("style", "")
        color_match = re.search(r"fill:\s*([^;]+)", style)
        color = color_match.group(1).strip() if color_match else "#6aa9ff"
        name = match.group(1)
        if name.lower() == "other":
            name = "Other"
        languages.append((name, int(match.group(2)), color))
    if not languages:
        raise RuntimeError("Could not read language activity from pie chart")
    return languages


def read_total_and_date(footer: ET.Element) -> tuple[int, str]:
    texts = [element for element in footer.iter(tag("text"))]
    total = None
    date_range = None
    for index, element in enumerate(texts):
        value = (element.text or "").strip()
        if value.lower() == "contributions" and index:
            total = int((texts[index - 1].text or "").strip())
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}\s*/\s*\d{4}-\d{2}-\d{2}", value):
            date_range = value.replace(" / ", " — ")
    if total is None or date_range is None:
        raise RuntimeError("Could not read contribution total and date range")
    return total, date_range


def build_grid(
    source: ET.Element,
    grid: ET.Element,
    total: int,
    date_range: str,
) -> ET.Element:
    width, height = 1280, 850
    output = svg_root(width, height)
    style = source.find(tag("style"))
    background = source.find(tag("rect"))
    if style is None or background is None:
        raise RuntimeError(f"Missing SVG style or background in {SOURCE}")
    output.append(copy.deepcopy(style))
    output.append(copy.deepcopy(background))
    output.append(copy.deepcopy(grid))

    set_text(output, "Contribution activity", x=40, y=44, size=26, color="#eeeeff", weight=700)
    set_text(output, "Past 12 months", x=40, y=72, size=15, color="#aaaaaa")
    set_text(output, date_range, x=1240, y=44, size=15, color="#aaaaaa", anchor="end")
    set_text(output, str(total), x=40, y=822, size=30, color="#ffc837", weight=700)
    set_text(output, "contributions", x=88, y=822, size=22, color="#eeeeff")
    return output


def build_insights(
    activity: list[tuple[str, int]],
    languages: list[tuple[str, int, str]],
) -> ET.Element:
    width, height = 1000, 380
    output = svg_root(width, height)
    ET.SubElement(
        output,
        tag("style"),
    ).text = '* { font-family: "Ubuntu", "Helvetica", "Arial", sans-serif; }'
    ET.SubElement(
        output,
        tag("rect"),
        {"x": "0", "y": "0", "width": str(width), "height": str(height), "fill": "#00000f"},
    )

    panels = [(24, 24, 460, 332), (516, 24, 460, 332)]
    for x, y, panel_width, panel_height in panels:
        ET.SubElement(
            output,
            tag("rect"),
            {
                "x": str(x),
                "y": str(y),
                "width": str(panel_width),
                "height": str(panel_height),
                "rx": "18",
                "fill": "#090b1a",
                "stroke": "#25283d",
                "stroke-width": "1.5",
            },
        )

    foreground, muted, accent = "#eeeeff", "#9b9caf", "#ffc837"
    set_text(output, "Contribution types", x=50, y=66, size=22, color=foreground, weight=700)
    set_text(output, "Past 12 months", x=50, y=90, size=14, color=muted)
    set_text(output, "Commit activity by language", x=542, y=66, size=22, color=foreground, weight=700)
    language_total = sum(count for _, count, _ in languages)
    set_text(
        output,
        f"{language_total} commits · top languages and other",
        x=542,
        y=90,
        size=14,
        color=muted,
    )

    for index, (label, count) in enumerate(activity):
        baseline = 132 + index * 42
        set_text(output, str(count), x=54, y=baseline, size=22, color=accent, weight=700)
        set_text(output, label, x=106, y=baseline, size=16, color=foreground)
        if index < len(activity) - 1:
            ET.SubElement(
                output,
                tag("line"),
                {
                    "x1": "50",
                    "y1": str(baseline + 12),
                    "x2": "458",
                    "y2": str(baseline + 12),
                    "stroke": "#1b1d30",
                    "stroke-width": "1",
                },
            )

    total = max(language_total, 1)
    bar_x, bar_width = 660, 180
    for index, (name, count, color) in enumerate(languages):
        baseline = 127 + index * 34
        set_text(output, name, x=542, y=baseline, size=15, color=foreground)
        ET.SubElement(
            output,
            tag("rect"),
            {"x": str(bar_x), "y": str(baseline - 10), "width": str(bar_width), "height": "9", "rx": "4.5", "fill": "#1a1c2b"},
        )
        fill_width = bar_width * count / total
        ET.SubElement(
            output,
            tag("rect"),
            {"x": str(bar_x), "y": str(baseline - 10), "width": f"{fill_width:.1f}", "height": "9", "rx": "4.5", "fill": color},
        )
        percentage = round(count * 100 / total)
        set_text(
            output,
            f"{count} · {percentage}%",
            x=952,
            y=baseline,
            size=14,
            color=muted,
            anchor="end",
        )
    return output


def main() -> None:
    source, grid, radar, language_panel, footer = read_source()
    activity = read_activity(radar)
    languages = read_languages(language_panel)
    total, date_range = read_total_and_date(footer)
    write_svg(ASSETS / "profile-grid.svg", build_grid(source, grid, total, date_range))
    write_svg(ASSETS / "profile-insights.svg", build_insights(activity, languages))


if __name__ == "__main__":
    main()
