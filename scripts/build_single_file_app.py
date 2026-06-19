#!/usr/bin/env python3
"""Build the GitHub Pages single-file app from the structured source files."""

from __future__ import annotations

import base64
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = ROOT / "index.template.html"
INDEX_PATH = ROOT / "index.html"
STYLE_PATH = ROOT / "styles.css"
DATA_PATH = ROOT / "data.js"
APP_PATH = ROOT / "app.js"
LOGO_PATH = ROOT / "assets" / "inspection-files-logo.jpg"


def main() -> None:
    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    css = STYLE_PATH.read_text(encoding="utf-8")
    data_js = DATA_PATH.read_text(encoding="utf-8")
    app_js = APP_PATH.read_text(encoding="utf-8")
    logo_data = base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")

    html = html.replace('<link rel="stylesheet" href="styles.css">', f"<style>\n{css}\n    </style>")
    html = html.replace(
        'src="assets/inspection-files-logo.jpg"',
        f'src="data:image/jpeg;base64,{logo_data}"',
    )
    html = html.replace(
        '    <script src="data.js?v=daily-refresh"></script>\n'
        '    <script src="app.js?v=daily-refresh"></script>',
        f"    <script>\n{data_js}\n    </script>\n    <script>\n{app_js}\n    </script>",
    )

    INDEX_PATH.write_text(html, encoding="utf-8")
    print(f"Wrote single-file app to {INDEX_PATH}")


if __name__ == "__main__":
    main()
