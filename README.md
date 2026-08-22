# Hoerspiel Explorer

A data-engineering portfolio for discovering German audio dramas through
structured metadata, entity resolution, analytics and retrieval.

> **Public catalog maintenance:** The original scraping pipeline demonstrated
> the end-to-end architecture, but its source basis is being reviewed. The live
> site therefore shows a maintenance/portfolio page while a provenance-first,
> API-backed catalog is evaluated. No data was deleted.

## Live Demo

[hoerspiel-explorer.azurestaticapps.net](https://lemon-flower-0536a4603.7.azurestaticapps.net)

## Project Goal

Audio dramas are difficult to explore because catalogs mix stories,
productions, physical editions, digital releases and box sets. This project
builds the data model and pipelines needed to distinguish those layers and
enable:

- semantic search across audio dramas
- filtering by themes (e.g. Christmas, Halloween, crime)
- mood-based exploration (e.g. cozy, dark, funny)
- recommendation of similar content via a conversational interface

## Architecture

```text
DNB / MusicBrainz ──→ canonical metadata ──→ Supabase ──→ dbt
Apple / Spotify   ──→ API-backed catalog  ──↗              │
Publisher feeds  ──→ licensed text assets ────────────────→│
                                                            ↓
                                            Next.js discovery + RAG
```

## Current Status

- **Public frontend**: reversible maintenance mode during the source review
- **Coverage research**: read-only iTunes Search API pilot for 20 series
- **Source strategy**: DNB and MusicBrainz core data for persistable provenance;
  commercial catalogs as terms-compliant API integrations
- **Data modeling**: canonical episodes separated from productions, releases
  and containers
- **Analytics prototype**: dbt staging, tested marts, Prefect orchestration and
  generated documentation retained as portfolio work
- **RAG roadmap**: only licensed descriptions or approved structured metadata
  will be embedded in the rebuilt public version

## Modules

### Historical ingestion prototype
The Flask, Prefect, parsing and cleaning components remain in the repository as
an implementation record. They are not the planned source of the rebuilt
public catalog.

→ [scraper/README.md](scraper/README.md)

### Parser & Cleaner
The historical parser demonstrates extraction and normalization of:
- episode metadata (title, description, duration, release date)
- speaker and role assignments
- genre tags
- speaker name normalization (umlaut variants)
- stub records for episodes without detail pages

### Database and analytics
The prototype uses a normalized PostgreSQL schema hosted on Supabase:
- `episodes`, `series`, `speakers`, `roles`, `genres`
- junction tables for many-to-many relationships
- `pgvector` extension for semantic similarity search
- `ivfflat` index for fast approximate nearest neighbor search

The next catalog iteration adds field-level provenance and a rights policy for
text assets. See [the data provenance strategy](docs/data-provenance-strategy.md).

### Frontend
The Next.js application currently presents the rebuild as a portfolio
maintenance page. The previous series, episode, chat and analytics routes can
be restored with one environment switch after the publication decision.

## Tech Stack

- **Python** — scraping, parsing, cleaning, data loading, RAG pipeline
- **requests** — rate-limited API clients and coverage analysis
- **Flask** — scraper dashboard
- **pandas** — data exploration
- **Supabase** — PostgreSQL + pgvector
- **dbt** — tested staging models, analytics marts, lineage, and documentation
- **Prefect** — observable scraping, loading, and analytics flows on a self-hosted worker
- **OpenAI** — text embeddings
- **Google Gemini** — LLM inference (free tier)
- **Next.js** — frontend with App Router and TypeScript
- **Tailwind CSS** — styling
- **Azure Static Web Apps** — frontend hosting (free tier)
- **GitHub Actions** — CI/CD pipeline
- **Docker / Docker Swarm** — containerized scraper deployment

## Coverage pilot

`analyze-itunes-coverage` uses the public iTunes Search API without an Apple
Music developer token. It only creates a private aggregate report and does not
load Apple metadata into Supabase. See
[the provenance strategy](docs/data-provenance-strategy.md) for limits,
operation and the plan for descriptions.

## Roadmap

Planned discovery and data-quality work, including speaker search and the
separation of canonical episodes from publication variants, is tracked in
[docs/product-backlog.md](docs/product-backlog.md).
