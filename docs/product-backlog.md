# Product and data-quality backlog

This document captures planned capabilities that are deliberately outside the
current analytics release.

## Speaker search

Add a first-class speaker search to the discovery frontend.

Planned behavior:

- search normalized speaker names with typo-tolerant matching;
- show matching speakers before individual episode credits;
- provide a speaker detail page with roles, series, episode counts and years;
- link speaker results to the existing episode and series pages;
- keep aliases and genuinely different people separate until an explicit,
  reviewable alias mapping exists.

The likely implementation is a narrowly exposed Supabase RPC backed by a
normalized search column and a PostgreSQL trigram index. The frontend must use
typed results and retain the existing RLS boundary.

## Canonical episodes and publication variants

The source catalog often represents the same narrative episode multiple times,
for example as an original release, LP/EP/MC/CD edition, special edition,
fan box or compilation. These rows must not simply be deleted: they are valid
publications, but counting every publication as a distinct episode distorts
discovery and analytics.

The first read-only profiling pilot is implemented for the `Die Drei ???`
main series. It exports classifications and relationship proposals for manual
review; it does not yet create canonical IDs. See
[`episode-variant-review.md`](episode-variant-review.md).

### Target model

Separate the conceptual work from its physical or commercial releases:

- `canonical_episodes`: one row for the narrative episode or work;
- `episode_editions`: existing source records linked to a canonical episode;
- `edition_category`: original, reissue, format variant, box set,
  compilation, special edition or unknown;
- `canonicalization_overrides`: reviewed mappings that take precedence over
  automatic rules and remain version-controlled.

The source episode and its `source_key` remain unchanged. Canonicalization is
an additional reversible layer, not a destructive merge.

### Automatic candidate generation

Create grouping candidates from several independent signals:

1. Normalize series, episode number and title while retaining the original
   values.
2. Extract publication markers such as `LP`, `EP`, `MC`, `CD`, `Fanbox`,
   `Sonderausgabe`, `Neuauflage`, `Box` and `Teil 1/2` into separate features.
3. Compare title similarity only within a compatible franchise or series.
4. Use supporting evidence such as order number, release date, duration,
   description similarity and speaker/role fingerprints.
5. Assign a confidence score and reasons to every proposed link.

High-confidence candidates may be linked automatically. Medium-confidence
candidates go into a review table; low-confidence candidates stay separate.
Different adaptations with the same title must never be merged from title
similarity alone.

### Rollout

1. Profile the largest affected franchises, beginning with `Die drei ???`, and
   create labeled examples for true duplicates and distinct adaptations.
2. Implement feature extraction and a candidate dbt model without changing
   product data.
3. Measure precision on the labeled sample and prefer false negatives over
   incorrect merges.
4. Add reviewable overrides and only then publish canonical episode IDs.
5. Let analytics expose both `canonical_episode_count` and
   `publication_count`; discovery groups editions beneath one canonical entry.
6. Apply the same rules to other series only after franchise-independent
   signals have been validated.

### Acceptance criteria

- every current source record remains traceable and reversible;
- automatic links include confidence and human-readable reasons;
- manual overrides are stable across rebuilds;
- repeated releases no longer inflate canonical episode statistics;
- box sets and compilations can reference multiple canonical episodes;
- distinct productions with identical titles remain separate.
