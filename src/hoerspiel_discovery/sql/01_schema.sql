CREATE TABLE series (
    id    SERIAL PRIMARY KEY,
    name  TEXT NOT NULL UNIQUE,
    label TEXT
);

CREATE TABLE episodes (
    id               BIGSERIAL PRIMARY KEY,
    series_id        INTEGER REFERENCES series(id),
    episode_number   BIGINT,
    title            TEXT,
    description      TEXT,
    duration_minutes REAL,
    release_date     DATE,
    cover_url        TEXT,
    order_number     TEXT,
    source_key       TEXT NOT NULL UNIQUE,
    source_url       TEXT UNIQUE,
    embedding        vector(1536)
);

CREATE TABLE speakers (
    id   SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE roles (
    id   SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE episode_speakers (
    episode_id INTEGER REFERENCES episodes(id),
    speaker_id INTEGER REFERENCES speakers(id),
    role_id    INTEGER REFERENCES roles(id),
    PRIMARY KEY (episode_id, speaker_id, role_id)
);

CREATE TABLE genres (
    id   SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE episode_genres (
    episode_id INTEGER REFERENCES episodes(id),
    genre_id   INTEGER REFERENCES genres(id),
    PRIMARY KEY (episode_id, genre_id)
);

CREATE TABLE scrape_targets (
    id              SERIAL PRIMARY KEY,
    source          TEXT NOT NULL DEFAULT 'hoerspiele.de',
    external_id     INTEGER NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',  -- pending | success | not_found | error
    attempts        INTEGER NOT NULL DEFAULT 0,
    last_attempt_at TIMESTAMPTZ,
    error_message   TEXT,
    UNIQUE (source, external_id)
);
