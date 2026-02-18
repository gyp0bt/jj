"""Utility functions (no ML framework imports)."""

import os
import json


def load_json(path):
    with open(path) as f:
        return json.load(f)


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)
