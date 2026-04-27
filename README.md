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

Scraper → Parser → Cleaner → Supabase (PostgreSQL + pgvector) → RAG Pipeline → Next.js Frontend

## Current Status

- **Scraper**: operational — 24,000+ episodes collected across 1,400+ series
- **Parser / Cleaner**: complete — speaker and role normalization, stub records for episodes without detail pages
- **Database**: complete — normalized schema in Supabase (episodes, series, speakers, roles, genres)
- **Embeddings**: in progress — generating vectors with OpenAI text-embedding-3-small
- **RAG Pipeline**: in progress
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

### Embeddings & RAG
- Episode embeddings generated with OpenAI `text-embedding-3-small`
- Similarity search via pgvector
- Conversational interface powered by Groq (cost-efficient, free tier)

## Tech Stack

- **Python** — scraping, parsing, cleaning, data loading
- **BeautifulSoup / requests** — HTML parsing and HTTP
- **Flask** — scraper dashboard
- **pandas** — data exploration
- **Supabase** — PostgreSQL + pgvector
- **OpenAI** — text embeddings
- **Docker / Docker Swarm** — containerized scraper deployment