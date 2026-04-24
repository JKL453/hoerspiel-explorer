from __future__ import annotations

import re
from pathlib import Path

from bs4 import BeautifulSoup, Tag
from urllib.parse import urljoin


def load_html(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def get_detail_cells(soup: BeautifulSoup) -> tuple[Tag | None, Tag | None, Tag | None]:
    detail_table = soup.find("table", attrs={"background": "img/backgrounds/BG_hsp_dynamisch.gif"})
    if detail_table is None:
        return None, None, None

    cells = detail_table.find_all("td")

    path_cell = None
    description_cell = None
    speakers_cell = None

    for cell in cells:
        width = cell.get("width")
        align = cell.get("align")
        valign = cell.get("valign")

        if width == "75%" and align == "left" and valign == "top":
            path_cell = cell
        elif width == "35%" and align == "justify" and valign == "top":
            description_cell = cell
        elif width == "35%" and align == "left" and valign == "top":
            speakers_cell = cell

    return path_cell, description_cell, speakers_cell




def extract_duration(description_cell: Tag | None) -> float | None:
    if description_cell is None:
        return None

    text = description_cell.get_text(" ", strip=True)
    match = re.search(r"Dauer:\s*([\d\.,]+)\s*Minuten", text)
    if not match:
        return None

    return float(match.group(1).replace(",", "."))


def extract_release_date(description_cell: Tag | None) -> str | None:
    if description_cell is None:
        return None

    text = description_cell.get_text(" ", strip=True)
    match = re.search(r"(\d{2}\.\d{2}\.\d{4})", text)
    if not match:
        return None

    return match.group(1)


def extract_path_metadata(path_cell: Tag | None) -> dict[str, str | int | None]:
    result: dict[str, str | int | None] = {
        "series_name": None,
        "episode_number": None,
        "title": None,
        "label": None,
    }

    if path_cell is None:
        return result

    series_link = path_cell.find("a", href=lambda href: href and "hsp_serie.asp?serie=" in href)
    if series_link is not None:
        result["series_name"] = series_link.get_text(strip=True)

    detail_links = path_cell.find_all("a", href=lambda href: href and "hsp_anzeige.asp?code=" in href)
    if len(detail_links) >= 2:
        episode_number_text = detail_links[0].get_text(strip=True)
        if episode_number_text.isdigit():
            result["episode_number"] = int(episode_number_text)
        result["title"] = detail_links[1].get_text(strip=True)

    label_link = path_cell.find("a", href=lambda href: href and "hsp_serienanzeige.asp?verlag=" in href)
    if label_link is not None:
        result["label"] = label_link.get_text(strip=True)

    return result


def extract_cover_url(soup: BeautifulSoup) -> str | None:
    cover_img = soup.find("img", src=lambda src: src and "bilder/bilder/" in src)
    if cover_img is None:
        return None

    src = cover_img.get("src")
    if not src:
        return None

    return urljoin("https://www.hoerspiele.de/", src)


def extract_speakers(speakers_cell: Tag | None) -> list[dict[str, str]]:
    if speakers_cell is None:
        return []

    speakers: list[dict[str, str]] = []
    rows = speakers_cell.find_all("tr")

    for row in rows:
        cells = row.find_all("td")
        if len(cells) != 4:
            continue

        role = cells[1].get_text(" ", strip=True)
        speaker = cells[3].get_text(" ", strip=True)

        if not role or not speaker:
            continue

        if role == "Rolle" or speaker == "Sprecher/in":
            continue

        speakers.append({"role": role, "speaker": speaker})

    return speakers


def extract_description(description_cell: Tag | None) -> str | None:
    if description_cell is None:
        return None

    for span in description_cell.find_all("span", class_="t4_bold"):
        span_text = " ".join(span.get_text(" ", strip=True).split())
        if "Beschreibung:" in span_text:
            description_span = span.find_next("span", class_="t5")
            if description_span is None:
                return None

            description = " ".join(description_span.get_text(" ", strip=True).split())
            return description or None

    return None


def extract_order_number(description_cell: Tag | None) -> str | None:
    if description_cell is None:
        return None

    text = description_cell.get_text(" ", strip=True)
    match = re.search(r"Bestellnummer:\s*(?:CD:\s*)?([^\s]+)", text)
    if not match:
        return None

    return match.group(1)


def extract_genres(soup: BeautifulSoup) -> list[str]:
    genres: list[str] = []

    for td in soup.find_all("td"):
        text = " ".join(td.get_text(" ", strip=True).split())
        if text.startswith("- "):
            genre = text.removeprefix("- ").strip()
            if genre:
                genres.append(genre)

    return genres


def extract_previous_episode_url(path_cell: Tag | None) -> str | None:
    if path_cell is None:
        return None

    full_text = " ".join(path_cell.get_text(" ", strip=True).split()).lower()
    if "keine folge davor" in full_text:
        return None

    links = path_cell.find_all("a", href=True)
    detail_links = [
        link for link in links
        if "hsp_anzeige.asp?code=" in link["href"]
    ]

    if len(detail_links) >= 3:
        return urljoin("https://www.hoerspiele.de/", detail_links[2]["href"])

    return None


def extract_next_episode_url(path_cell: Tag | None) -> str | None:
    if path_cell is None:
        return None

    detail_links = path_cell.find_all(
        "a",
        href=lambda href: href and "hsp_anzeige.asp?code=" in href,
    )

    if len(detail_links) >= 3:
        return urljoin("https://www.hoerspiele.de/", detail_links[-1]["href"])

    return None


def extract_source_url(path_cell) -> str | None:
    if path_cell is None:
        return None
    detail_links = path_cell.find_all(
        "a", href=lambda h: h and "hsp_anzeige.asp?code=" in h
    )
    if not detail_links:
        return None
    return urljoin("https://www.hoerspiele.de/", detail_links[0]["href"])



def parse_detail_page(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    path_cell, description_cell, speakers_cell = get_detail_cells(soup)
    path_metadata = extract_path_metadata(path_cell)

    result = {
        "title": path_metadata["title"],
        "series_name": path_metadata["series_name"],
        "episode_number": path_metadata["episode_number"],
        "description": extract_description(description_cell),
        "duration_minutes": extract_duration(description_cell),
        "release_date": extract_release_date(description_cell),
        "label": path_metadata["label"],
        "cover_url": extract_cover_url(soup),
        "speakers": extract_speakers(speakers_cell),
        "order_number": extract_order_number(description_cell),
        "genres": extract_genres(soup),
        "previous_episode_url": extract_previous_episode_url(path_cell),
        "next_episode_url": extract_next_episode_url(path_cell),
        "source_url": extract_source_url(path_cell),
    }

    return result


def main() -> None:
    path = Path("data/raw/detail_pages/https_www_hoerspiele_de_hsp_anzeige_asp_code_9773_fb172aab0c.html")
    html = load_html(path)
    parsed = parse_detail_page(html)

    soup = BeautifulSoup(html, "lxml")
    
    path_cell, description_cell, speakers_cell = get_detail_cells(soup)

    print("\nDebug values:\n")
    print("path cell found:", path_cell is not None)
    print("description cell found:", description_cell is not None)
    print("speakers cell found:", speakers_cell is not None)
    print("description text:", extract_description(description_cell))
    print("duration value:", extract_duration(description_cell))
    print("release raw:", extract_release_date(description_cell))
    print("path metadata:", extract_path_metadata(path_cell))
    print("cover url:", extract_cover_url(soup))
    print("speaker count:", len(extract_speakers(speakers_cell)))

    print("order number:", extract_order_number(description_cell))
    print("genres:", extract_genres(soup))
    print("previous episode url:", extract_previous_episode_url(path_cell))
    print("next episode url:", extract_next_episode_url(path_cell))

    print("\nParsed result:\n")
    for key, value in parsed.items():
        print(f"{key}: {value}")
    print("order number:", extract_order_number(description_cell))
    print("genres:", extract_genres(soup))
    print("previous episode url:", extract_previous_episode_url(path_cell))
    print("next episode url:", extract_next_episode_url(path_cell))


if __name__ == "__main__":
    main()