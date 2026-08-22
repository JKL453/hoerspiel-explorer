# Data provenance and API coverage strategy

The public catalog is temporarily in maintenance mode while its data sources
are reviewed. The existing implementation remains useful as a technical
prototype, but its records are not the basis for new public features.

## Coverage pilot

The first experiment uses the public iTunes Search API. It requires no Apple
Music developer token and does not load results into Supabase. The Prefect
deployment `analyze-itunes-coverage` runs one rate-limited album search for 20
German audio-drama series and publishes an aggregate report to:

```text
/data/hoerspiel-explorer/review/itunes_coverage/
```

Each report records candidate counts, recognizable episode numbers, duplicate
title groups, year ranges and five examples for manual inspection. A query
returning 200 rows is marked as truncated because it reached the API limit.
The pilot deliberately stores neither full API responses nor a public Apple
catalog mirror.

The first completed run on 2026-08-22 found 2,580 candidate releases and 1,946
distinct recognizable episode numbers across the 20 probes. Eight searches
reached the 200-result ceiling, so these are lower bounds rather than complete
catalog counts. This is sufficient evidence to continue with a federated API
prototype instead of limiting the project to a small DNB-only catalog.

The iTunes Search API documentation currently describes a limit of roughly 20
calls per minute and recommends caching for larger sites. Artwork and previews
are promotional content: their display must follow Apple's linking,
attribution and usage requirements.

- [iTunes Search API overview](https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/index.html)
- [Search parameters and limits](https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/Searching.html)
- [Apple Music API](https://developer.apple.com/documentation/AppleMusicAPI)

## Intended source roles

| Source | Intended role | Persistence |
|---|---|---|
| DNB | Bibliographic identifiers and release facts | CC0 data may be stored with provenance |
| MusicBrainz core | Releases, recordings, barcodes and relationships | CC0 core data may be stored |
| Apple/iTunes | Coverage, current catalog links and permitted promotional display | API-backed; no independent mirror |
| Spotify | Optional current-catalog fallback | API-backed with Spotify attribution and links |
| Publishers | Authoritative descriptions, covers and production metadata | Only with feed terms or written permission |
| Retailers | Outbound discovery links | No scraping without permission |

API conditions can change. Every provider therefore needs its own adapter and
source policy instead of copying fields into an undocumented generic import.

## Descriptions and RAG

Descriptions remain a product goal, but public availability is not itself a
reuse license. Attribution also does not replace permission. Future text
assets should be stored separately from factual metadata with at least:

- provider and original URL;
- text type (`publisher_blurb`, `editorial_summary`, `user_annotation`);
- license or written permission reference;
- required attribution;
- whether storage, public display and embedding are individually permitted;
- review date and content hash.

Only assets explicitly allowed for embedding enter the RAG index. Suitable
paths are publisher feeds or written permissions, licensed API fields,
original editorial summaries and contributed annotations under clear terms.
Scraped blurbs and AI paraphrases made from unlicensed blurbs are not accepted
as a workaround.

Before descriptions are available, the retrieval document can be generated
from permitted structured facts: series, canonical episode title and number,
production line, release year, label, carrier, track titles, genres and curated
tags. This supports a useful metadata-based RAG prototype without silently
indexing protected prose.

## Maintenance mode

The frontend defaults to maintenance mode. Production CI explicitly sets:

```text
NEXT_PUBLIC_CATALOG_MODE=maintenance
```

Setting it to `legacy` and redeploying restores the previous routes and chat.
That switch is technical and reversible, but should only happen after the data
publication decision has been reviewed.
