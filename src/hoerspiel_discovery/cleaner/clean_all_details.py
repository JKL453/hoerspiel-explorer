from __future__ import annotations

import json

from hoerspiel_discovery.cleaner.clean_detail import clean_detail_record
from hoerspiel_discovery.config import INTERIM_DATA_DIR


def main() -> None:
    input_path = INTERIM_DATA_DIR / "parsed_details.json"
    output_path = INTERIM_DATA_DIR / "cleaned_details.json"

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    records = json.loads(input_path.read_text(encoding="utf-8"))

    cleaned_records = [clean_detail_record(record) for record in records]

    output_path.write_text(
        json.dumps(cleaned_records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Loaded {len(records)} parsed records")
    print(f"Saved {len(cleaned_records)} cleaned records to {output_path}")


if __name__ == "__main__":
    main()