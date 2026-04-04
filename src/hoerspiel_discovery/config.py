from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent.parent

DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
INTERIM_DATA_DIR = DATA_DIR / "interim"

RAW_SERIES_PAGES_DIR = RAW_DATA_DIR / "series_pages"
RAW_DETAIL_PAGES_DIR = RAW_DATA_DIR / "detail_pages"