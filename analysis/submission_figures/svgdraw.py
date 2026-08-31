"""Tiny SVG builder. No layout engine: every coordinate is explicit."""
from __future__ import annotations

from dataclasses import dataclass, field
from html import escape
from pathlib import Path

FONT = "Helvetica Neue, Helvetica, Arial, sans-serif"
INK = "#1a1a1a"
MUTED = "#5c5c5c"
FAINT = "#d8d8d8"
RULE = "#8a8a8a"
BELOW = "#0072B2"
ABOVE = "#E69F00"


def _style(**kwargs) -> str:
    parts = []
    for key, value in kwargs.items():
        if value is None:
            continue
        name = key.replace("_", "-")
        parts.append(f'{name}="{escape(str(value), quote=True)}"')
    return (" " + " ".join(parts)) if parts else ""


@dataclass
class Svg:
    width: float
    height: float
    nodes: list[str] = field(default_factory=list)

    def add(self, markup: str) -> None:
        self.nodes.append(markup)

    def rect(self, x, y, w, h, *, fill="none", stroke=None, sw=1, rx=0) -> None:
        extra = f' rx="{rx}"' if rx else ""
        stroke_attr = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
        self.add(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}"'
            f' fill="{fill}"{stroke_attr}{extra}/>'
        )

    def line(self, x1, y1, x2, y2, *, stroke=RULE, sw=1, dash=None, cap="butt") -> None:
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}"'
            f' stroke="{stroke}" stroke-width="{sw}" stroke-linecap="{cap}"{dash_attr}/>'
        )

    def circle(self, x, y, r, *, fill, stroke="none", sw=0.6, opacity=1) -> None:
        self.add(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r}" fill="{fill}"'
            f' stroke="{stroke}" stroke-width="{sw}" opacity="{opacity}"/>'
        )

    def clip_start(self, name: str, x, y, w, h) -> None:
        self.add(
            f'<defs><clipPath id="{name}">'
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}"/>'
            f"</clipPath></defs>"
            f'<g clip-path="url(#{name})">'
        )

    def clip_end(self) -> None:
        self.add("</g>")

    def text(
        self,
        x,
        y,
        content,
        *,
        size=13,
        fill=INK,
        weight=400,
        anchor="start",
        baseline="alphabetic",
        italic=False,
    ) -> None:
        font_style = "italic" if italic else "normal"
        lines = str(content).split("\n")
        if len(lines) == 1:
            self.add(
                f'<text x="{x:.2f}" y="{y:.2f}" fill="{fill}" font-size="{size}"'
                f' font-weight="{weight}" font-family="{FONT}" font-style="{font_style}"'
                f' text-anchor="{anchor}" dominant-baseline="{baseline}">'
                f"{escape(lines[0])}</text>"
            )
            return
        self.add(
            f'<text x="{x:.2f}" y="{y:.2f}" fill="{fill}" font-size="{size}"'
            f' font-weight="{weight}" font-family="{FONT}" font-style="{font_style}"'
            f' text-anchor="{anchor}" dominant-baseline="{baseline}">'
        )
        for i, line in enumerate(lines):
            dy = "0" if i == 0 else f"{round(size * 1.28, 1)}"
            self.add(f'<tspan x="{x:.2f}" dy="{dy}">{escape(line)}</tspan>')
        self.add("</text>")

    def to_string(self) -> str:
        body = "\n".join(self.nodes)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width:.0f}" '
            f'height="{self.height:.0f}" viewBox="0 0 {self.width:.0f} {self.height:.0f}">\n'
            f'<rect width="100%" height="100%" fill="white"/>\n'
            f"{body}\n</svg>\n"
        )

    def write(self, path: Path) -> Path:
        path.write_text(self.to_string())
        return path
