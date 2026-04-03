from __future__ import annotations

import hashlib
import re
from pathlib import Path

import certifi
import requests

from hoerspiel_discovery.config import RAW_DATA_DIR


def slugify_url(url: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", url).strip("_").lower()
    return slug[:80]


def build_file_name(url: str) -> str:
    url_hash = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]
    slug = slugify_url(url)
    return f"{slug}_{url_hash}.html"


def fetch_page(url: str, timeout: int = 15) -> str:
    headers = {
        "User-Agent": (
            "hoerspiel-explorer/0.1 "
            "(learning project; respectful crawling)"
        )
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=timeout,
        verify=certifi.where(),
    )
    response.raise_for_status()
    return response.text


def save_html(html: str, target_dir: Path, source_url: str) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    file_name = build_file_name(source_url)
    output_path = target_dir / file_name
    output_path.write_text(html, encoding="utf-8")
    return output_path


def main() -> None:
    url = "https://example.com"
    html = fetch_page(url)
    saved_path = save_html(html=html, target_dir=RAW_DATA_DIR, source_url=url)
    print(f"Saved HTML to {saved_path}")


if __name__ == "__main__":
    main()