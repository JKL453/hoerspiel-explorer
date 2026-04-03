# Hoerspiel Explorer

A data-driven platform for discovering German audio dramas through structured metadata, thematic filtering, and recommendation techniques.

## 🚀 Project Goal

Audio dramas (Hörspiele) are often difficult to explore beyond simple title or series search.  
This project aims to build a discovery platform that enables:

- semantic search across audio dramas
- filtering by themes (e.g. Christmas, Halloween, crime)
- mood-based exploration (e.g. cozy, dark, funny)
- recommendation of similar content

---

## 🏗️ Planned Architecture

Scraper → Parser → Cleaner → Database → API → Frontend

---

## 📦 Current Status

- Project setup completed
- Initial scraping prototype implemented
- Raw HTML storage working
- SSL issue under investigation (local environment)

---

## 🧰 Tech Stack (planned)

- Python
- BeautifulSoup / requests
- PostgreSQL
- FastAPI
- Docker
- Azure (Free Tier)
- Optional: Airflow, embeddings, vector search