from __future__ import annotations

import json
from typing import Any


def load_latest_watermarks(watermark_dir: str) -> dict[str, Any]:
    """
    Load the most recent watermark file from a Fabric Lakehouse folder.

    The latest file is chosen by file name, so watermark files should use
    sortable names such as timestamps.

    Returns {} when the folder cannot be listed or contains no .json files.

    Requires the Microsoft Fabric notebook runtime.
    """
    import notebookutils

    try:
        files = [
            f
            for f in notebookutils.fs.ls(watermark_dir)
            if not f.isDir and f.name.endswith(".json")
        ]
    except Exception:
        return {}

    if not files:
        print("No watermark files found.")
        return {}

    latest_file = max(files, key=lambda f: f.name)
    print(f"Loading watermarks from {latest_file.name}")

    return json.loads(notebookutils.fs.head(latest_file.path, 10_000_000))
