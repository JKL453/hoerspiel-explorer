from __future__ import annotations

import json
from pathlib import Path

from hoerspiel_discovery.config import RAW_DETAIL_PAGES_DIR, INTERIM_DATA_DIR
from hoerspiel_discovery.parser.parse_detail import load_html, parse_detail_page


def main() -> None:
    INTERIM_DATA_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    html_files = sorted(RAW_DETAIL_PAGES_DIR.glob("*.html"))

    print(f"Found {len(html_files)} detail pages")

    for i, path in enumerate(html_files, start=1):
        print(f"[{i}/{len(html_files)}] Parsing {path.name}")
        html = load_html(path)
        parsed = parse_detail_page(html)
        parsed["source_file"] = path.name
        results.append(parsed)

    output_path = INTERIM_DATA_DIR / "parsed_details.json"
    output_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Saved parsed data to {output_path}")


if __name__ == "__main__":
    main()