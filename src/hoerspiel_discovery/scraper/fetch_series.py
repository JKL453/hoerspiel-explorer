from __future__ import annotations

import hashlib
import re
import time
from pathlib import Path

import certifi
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from hoerspiel_discovery.config import RAW_SERIES_PAGES_DIR


def slugify_url(url: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", url).strip("_").lower()
    return slug[:80]


def build_file_name(url: str) -> str:
    url_hash = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]
    slug = slugify_url(url)
    return f"{slug}_{url_hash}.html"


def polite_delay(seconds: float = 3.0) -> None:
    time.sleep(seconds)


def fetch_page(url: str, timeout: int = 20) -> str:
    headers = {
        "User-Agent": (
            "hoerspiel-explorer/0.1 "
            "(personal learning project; respectful crawling; low frequency)"
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


def extract_episode_links(html: str, base_url: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    results = []
    seen = set()

    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 3:
            continue

        # Identify episode rows by series link in first cell
        series_link = cells[0].find(
            "a", href=lambda h: h and "hsp_serie.asp?serie=" in h
        )
        if not series_link:
            continue

        series_name = series_link.get_text(strip=True)

        # Episode number from second cell
        episode_number_text = cells[1].get_text(strip=True).rstrip("\xa0").strip()
        episode_number = int(episode_number_text) if episode_number_text.isdigit() else None

        # Title cell — check for detail link or plain text
        title_cell = cells[2]
        detail_link = title_cell.find(
            "a", href=lambda h: h and "hsp_anzeige.asp?code=" in h
        )

        if detail_link:
            url = urljoin(base_url, detail_link["href"])
            title = detail_link.get_text(strip=True)
            has_detail_page = True
        else:
            url = None
            title = title_cell.get_text(strip=True)
            has_detail_page = False

        if not title or title in seen:
            continue

        seen.add(title)
        results.append({
            "url":            url,
            "title":          title,
            "episode_number": episode_number,
            "series_name":    series_name,
            "has_detail_page": has_detail_page,
        })

    return results


from hoerspiel_discovery.config import RAW_DETAIL_PAGES_DIR


def fetch_episode_pages(episodes: list[dict[str, str]]) -> None:
    for i, episode in enumerate(episodes, start=1):
        url = episode["url"]
        title = episode["title"]

        print(f"[{i}/{len(episodes)}] Fetching: {title}")

        file_name = build_file_name(url)
        output_path = RAW_DETAIL_PAGES_DIR / file_name

        # Skip wenn schon vorhanden
        if output_path.exists():
            print("  -> already exists, skipping")
            continue

        try:
            polite_delay(3.0)
            html = fetch_page(url)
            save_html(html, RAW_DETAIL_PAGES_DIR, url)
            print("  -> saved")

        except Exception as e:
            print(f"  -> ERROR: {e}")


def save_html(html: str, target_dir: Path, source_url: str) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    file_name = build_file_name(source_url)
    output_path = target_dir / file_name
    output_path.write_text(html, encoding="utf-8")
    return output_path


def main() -> None:
    url = "https://www.hoerspiele.de/hsp_serie.asp?serie=738"

    polite_delay()

    html = fetch_page(url)
    saved_path = save_html(html=html, target_dir=RAW_SERIES_PAGES_DIR, source_url=url)

    print(f"Saved series page to {saved_path}")

    episode_links = extract_episode_links(html, base_url=url)
    print(f"Found {len(episode_links)} episode links")

    for item in episode_links[:5]:
        print(item["title"], "->", item["url"])

    print("\n--- Start fetching detail pages ---\n")

    fetch_episode_pages(episode_links)


if __name__ == "__main__":
    main()