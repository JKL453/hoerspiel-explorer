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