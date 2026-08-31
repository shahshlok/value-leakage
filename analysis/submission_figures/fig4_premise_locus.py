"""Canonical figures: uv run python analysis/submission_figures/render.py"""
from render import fig4, rasterize

if __name__ == "__main__":
    path, w, h = fig4()
    rasterize(path, path.with_suffix(".png"), w, h)
    print(path)
