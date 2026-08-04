from datetime import datetime, timezone
from prefect import task
from dotenv import load_dotenv
from supabase import create_client
import os

load_dotenv()
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])


@task
def update_scrape_target_status(result: dict, error: str | None = None):
    """Writes the fetch outcome back to scrape_targets."""
    update_data = {
        "status": result["status"] if not error else "error",
        "last_attempt_at": datetime.now(timezone.utc).isoformat(),
    }
    if result.get("html_path"):
        update_data["html_path"] = result["html_path"]
    if error:
        update_data["error_message"] = error

    supabase.table("scrape_targets").update(update_data).eq(
        "external_id", result["external_id"]
    ).execute()


def get_pending_targets() -> list[int]:
    """Not a Prefect task — plain helper, called once at flow start."""
    all_ids = []
    page_size = 1000
    offset = 0

    while True:
        response = (
            supabase.table("scrape_targets")
            .select("external_id")
            .in_("status", ["pending", "error"])
            .range(offset, offset + page_size -1)
            .execute()
        )
        rows = response.data
        if not rows:
            break
        all_ids.extend(row["external_id"] for row in rows)
        offset += page_size

    return all_ids


def get_scraped_series() -> list[dict]:
    """Returns external_id and html_path for all successfully scraped series."""
    all_rows = []
    page_size = 1000
    offset = 0

    while True:
        response = (
            supabase.table("scrape_targets")
            .select("external_id, html_path")
            .eq("status", "success")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        rows = response.data
        if not rows:
            break
        all_rows.extend(rows)
        offset += page_size

    return all_rows