"""
One-time script to seed scrape_targets with the full range of IDs
to be scraped. Run manually before starting the Prefect scrape flow.
"""

from dotenv import load_dotenv
from supabase import create_client
import os

load_dotenv()
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

SOURCE = "hoerspiele.de"
MIN_ID = 1
MAX_ID = 3000  # adjust
BATCH_SIZE = 500


def seed_scrape_targets():
    all_ids = range(MIN_ID, MAX_ID + 1)

    for i in range(0, len(all_ids), BATCH_SIZE):
        batch = list(all_ids[i : i + BATCH_SIZE])
        rows = [
            {"source": SOURCE, "external_id": eid, "status": "pending"}
            for eid in batch
        ]
        supabase.table("scrape_targets").upsert(
            rows, on_conflict="source,external_id"
        ).execute()
        print(f"Seeded batch {i // BATCH_SIZE + 1}: IDs {batch[0]}–{batch[-1]}")

    print(f"Done. Seeded {MAX_ID - MIN_ID + 1} targets.")


if __name__ == "__main__":
    seed_scrape_targets()