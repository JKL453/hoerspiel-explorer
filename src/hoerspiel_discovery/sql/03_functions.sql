CREATE OR REPLACE FUNCTION match_episodes(
    query_embedding vector(1536),
    match_count     int DEFAULT 10,
    filter_genre    text DEFAULT NULL
)
RETURNS TABLE (
    id               bigint,
    title            text,
    series_name      text,
    episode_number   bigint,
    description      text,
    cover_url        text,
    release_date     date,
    duration_minutes real,
    similarity       float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.id,
        e.title,
        s.name AS series_name,
        e.episode_number,
        e.description,
        e.cover_url,
        e.release_date,
        e.duration_minutes,
        1 - (e.embedding <=> query_embedding) AS similarity
    FROM episodes e
    LEFT JOIN series s ON s.id = e.series_id
    WHERE e.embedding IS NOT NULL
      AND (filter_genre IS NULL OR EXISTS (
          SELECT 1 FROM episode_genres eg
          JOIN genres g ON g.id = eg.genre_id
          WHERE eg.episode_id = e.id AND g.name = filter_genre
      ))
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;


CREATE OR REPLACE FUNCTION get_series_with_episode_count()
RETURNS TABLE (
    id          bigint,
    name        text,
    label       text,
    episode_count bigint
)
LANGUAGE sql
AS $$
    SELECT 
        s.id,
        s.name,
        s.label,
        COUNT(e.id) as episode_count
    FROM series s
    LEFT JOIN episodes e ON e.series_id = s.id
    GROUP BY s.id, s.name, s.label
    ORDER BY episode_count DESC;
$$;


CREATE OR REPLACE FUNCTION get_episodes_by_speaker(speaker_id_input bigint)
RETURNS TABLE (
    episode_id   bigint,
    title        text,
    series_name  text,
    series_id    bigint,
    episode_number bigint,
    release_date date,
    duration_minutes real,
    cover_url    text,
    role_name    text
)
LANGUAGE sql
AS $$
    SELECT
        e.id as episode_id,
        e.title,
        s.name as series_name,
        s.id as series_id,
        e.episode_number,
        e.release_date,
        e.duration_minutes,
        e.cover_url,
        r.name as role_name
    FROM episode_speakers es
    JOIN episodes e ON e.id = es.episode_id
    JOIN series s ON s.id = e.series_id
    JOIN roles r ON r.id = es.role_id
    WHERE es.speaker_id = speaker_id_input
    ORDER BY s.name, e.episode_number;
$$;


-- ----- --
-- Stats --
-- ----- --

-- Episodes per year
CREATE OR REPLACE FUNCTION get_episodes_per_year()
RETURNS TABLE (year int, episode_count bigint)
LANGUAGE sql
AS $$
    SELECT
        EXTRACT(YEAR FROM release_date)::int AS year,
        COUNT(*) AS episode_count
    FROM episodes
    WHERE release_date IS NOT NULL
    GROUP BY year
    ORDER BY year;
$$;

-- Top genres
CREATE OR REPLACE FUNCTION get_top_genres(limit_count int DEFAULT 10)
RETURNS TABLE (genre_name text, episode_count bigint)
LANGUAGE sql
AS $$
    SELECT
        g.name AS genre_name,
        COUNT(*) AS episode_count
    FROM episode_genres eg
    JOIN genres g ON g.id = eg.genre_id
    GROUP BY g.name
    ORDER BY episode_count DESC
    LIMIT limit_count;
$$;

-- Top labels
CREATE OR REPLACE FUNCTION get_top_labels(limit_count int DEFAULT 10)
RETURNS TABLE (label_name text, series_count bigint)
LANGUAGE sql
AS $$
    SELECT
        label AS label_name,
        COUNT(*) AS series_count
    FROM series
    WHERE label IS NOT NULL AND label != '?'
    GROUP BY label
    ORDER BY series_count DESC
    LIMIT limit_count;
$$;