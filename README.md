# Hoerspiel Explorer

A data-driven platform for discovering German audio dramas through structured metadata, thematic filtering, and recommendation techniques.

## Project Goal

Audio dramas (Hörspiele) are often difficult to explore beyond simple title or series search.  
This project aims to build a discovery platform that enables:

- semantic search across audio dramas
- filtering by themes (e.g. Christmas, Halloween, crime)
- mood-based exploration (e.g. cozy, dark, funny)
- recommendation of similar content



## Planned Architecture

Scraper → Parser → Cleaner → Database → API → Frontend



## Current Status

- **Scraper**: operational — 7,600+ episodes collected across 1,279+ series (see [`scraper/`](scraper/README.md))
- Parser / Cleaner: in progress
- Database, API, Frontend: planned



## Modules

### Scraper
Flask-based dashboard and background worker that collects episode metadata from hoerspiele.de.  
Supports discovery mode (scanning series IDs up to a configurable Max-ID), single-series scraping, and pause/resume.

→ [scraper/README.md](scraper/README.md)


## Tech Stack

- Python, Flask
- BeautifulSoup / requests
- PostgreSQL (planned)
- FastAPI (planned)
- Docker / Docker Swarm + Traefik
- Azure (planned)