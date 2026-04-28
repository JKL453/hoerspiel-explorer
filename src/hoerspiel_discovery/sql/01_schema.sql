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