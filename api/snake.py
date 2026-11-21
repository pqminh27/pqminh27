"""Vercel entry point for the profile snake."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".github" / "scripts"))

from serve_snake import SnakeHandler


class handler(SnakeHandler):
    pass
