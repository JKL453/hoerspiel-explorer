# Hoerspiel Explorer

A data-driven platform for discovering German audio dramas through structured metadata, semantic search, and AI-powered recommendations.

## Project Goal

Audio dramas (Hörspiele) are often difficult to explore beyond simple title or series search.
This project aims to build a discovery platform that enables:

- semantic search across audio dramas
- filtering by themes (e.g. Christmas, Halloween, crime)
- mood-based exploration (e.g. cozy, dark, funny)
- recommendation of similar content via a conversational interface

## Architecture

Scraper → Parser → Cleaner → Supabase (PostgreSQL + pgvector) → RAG Pipeline → Frontend

## Current Status

- **Scraper**: operational — 24,000+ episodes collected across 1,400+ series
- **Parser / Cleaner**: complete — speaker and role normalization, stub records for episodes without detail pages
- **Database**: complete — normalized schema in Supabase (episodes, series, speakers, roles, genres)
- **Embeddings**: complete — 12,900+ episodes embedded with OpenAI text-embedding-3-small (title, series, description, genres, speakers)
- **RAG Pipeline**: complete — semantic search via pgvector + Google Gemini for response generation
- **Frontend**: planned

## Modules

### Scraper
Flask-based dashboard and background worker that collects episode metadata from hoerspiele.de.
Supports single-series scraping and pause/resume via web interface.

→ [scraper/README.md](scraper/README.md)

### Parser & Cleaner
Extracts structured data from raw HTML and normalizes it:
- episode metadata (title, description, duration, release date)
- speaker and role assignments
- genre tags
- speaker name normalization (umlaut variants)
- stub records for episodes without detail pages

### Database
Normalized PostgreSQL schema hosted on Supabase:
- `episodes`, `series`, `speakers`, `roles`, `genres`
- junction tables for many-to-many relationships
- `pgvector` extension for semantic similarity search
- `ivfflat` index for fast approximate nearest neighbor search

### Embeddings & RAG
- Episode embeddings generated with OpenAI `text-embedding-3-small`
- Embedding text combines title, series, description, genres and speakers for richer semantic context
- Similarity search via pgvector `match_episodes` function
- Response generation with Google Gemini (free tier)

## Tech Stack

- **Python** — scraping, parsing, cleaning, data loading, RAG pipeline
- **BeautifulSoup / requests** — HTML parsing and HTTP
- **Flask** — scraper dashboard
- **pandas** — data exploration
- **Supabase** — PostgreSQL + pgvector
- **OpenAI** — text embeddings
- **Google Gemini** — LLM inference (free tier)
- **Docker / Docker Swarm** — containerized scraper deployment

## Cost Architecture

A key design goal of this project is to minimize running costs while using production-grade infrastructure.

| Component | Service | Cost |
|---|---|---|
| Database + Vector Search | Supabase Free Tier | $0/month |
| Text Embeddings | OpenAI text-embedding-3-small | ~$0.02 one-time |
| LLM Inference | Google Gemini Free Tier | $0/month |
| Frontend Hosting | Azure Static Web Apps Free Tier | $0/month |
| Scraper | Docker Swarm (self-hosted) | $0/month |
| CI/CD | GitHub Actions | $0/month |

The only significant cost was the one-time embedding generation (~$0.02 for 12,900 episodes).
This approach demonstrates that production-ready AI applications can be built and operated
at near-zero cost by combining free tiers strategically.