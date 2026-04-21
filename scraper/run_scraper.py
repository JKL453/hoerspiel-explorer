"""
CLI-Einstiegspunkt — startet Flask-Dashboard + Scraper.

Verwendung:
  python run_scraper.py                          # nur Dashboard starten
  python run_scraper.py --series 738 1 202       # sofort Serien einreihen
  python run_scraper.py --series 738 --delay 5   # mit angepasstem Delay
  python run_scraper.py --port 8080              # anderen Port nutzen
"""
from __future__ import annotations

import argparse
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)

def main() -> None:
    parser = argparse.ArgumentParser(description="Hörspiel Scraper")
    parser.add_argument("--series", nargs="+", type=int, metavar="ID", help="Serien-IDs die sofort gestartet werden sollen")
    parser.add_argument("--delay",  type=float, default=3.0, help="Sekunden zwischen Requests (Standard: 3)")
    parser.add_argument("--port",   type=int,   default=5123, help="Port für das Dashboard (Standard: 5123)")
    args = parser.parse_args()

    from scraper.worker import worker
    from scraper.app import app

    if args.series:
        worker.delay = args.delay
        worker.enqueue(args.series)
        print(f"Serien eingereiht: {args.series}")

    print(f"Dashboard: http://localhost:{args.port}")
    app.run(host="0.0.0.0", port=args.port, debug=False)


if __name__ == "__main__":
    main()