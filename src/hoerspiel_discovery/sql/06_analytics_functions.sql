-- Run after the first successful build-dbt-analytics deployment.
-- The functions are SECURITY DEFINER so the browser never needs direct access
-- to the analytics schema. Only these narrow, read-only interfaces are exposed.

CREATE OR REPLACE FUNCTION public.get_analytics_kpis(
    start_year int DEFAULT NULL,
    end_year int DEFAULT NULL
)
RETURNS TABLE (
    episode_count bigint,
    series_count bigint,
    label_count bigint,
    franchise_count bigint,
    episodes_without_year bigint,
    episodes_without_duration bigint
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
    SELECT
        count(*)::bigint,
        count(DISTINCT facts.series_id)::bigint,
        count(DISTINCT facts.label_name)::bigint,
        count(DISTINCT facts.franchise_name)::bigint,
        count(*) FILTER (WHERE facts.release_year IS NULL)::bigint,
        count(*) FILTER (WHERE facts.duration_minutes IS NULL)::bigint
    FROM analytics.mart_episode_facts facts
    WHERE (start_year IS NULL OR facts.release_year >= start_year)
      AND (end_year IS NULL OR facts.release_year <= end_year);
$$;

CREATE OR REPLACE FUNCTION public.get_analytics_episodes_per_year(
    start_year int DEFAULT NULL,
    end_year int DEFAULT NULL
)
RETURNS TABLE (year int, episode_count bigint)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = ''
AS $$
    SELECT facts.release_year, count(*)::bigint
    FROM analytics.mart_episode_facts facts
    WHERE facts.release_year IS NOT NULL
      AND (start_year IS NULL OR facts.release_year >= start_year)
      AND (end_year IS NULL OR facts.release_year <= end_year)
    GROUP BY facts.release_year
    ORDER BY facts.release_year;
$$;

CREATE OR REPLACE FUNCTION public.get_analytics_genre_trends(
    start_year int DEFAULT NULL,
    end_year int DEFAULT NULL,
    limit_count int DEFAULT 5
)
RETURNS TABLE (year int, genre_name text, episode_count bigint)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = ''
AS $$
    WITH filtered AS (
        SELECT genres.*
        FROM analytics.mart_episode_genres genres
        WHERE genres.release_year IS NOT NULL
          AND (start_year IS NULL OR genres.release_year >= start_year)
          AND (end_year IS NULL OR genres.release_year <= end_year)
    ),
    top_genres AS (
        SELECT filtered.genre_name
        FROM filtered
        GROUP BY filtered.genre_name
        ORDER BY count(DISTINCT filtered.episode_id) DESC, filtered.genre_name
        LIMIT greatest(1, least(coalesce(limit_count, 5), 20))
    )
    SELECT
        filtered.release_year,
        filtered.genre_name,
        count(DISTINCT filtered.episode_id)::bigint
    FROM filtered
    JOIN top_genres USING (genre_name)
    GROUP BY filtered.release_year, filtered.genre_name
    ORDER BY filtered.release_year, filtered.genre_name;
$$;

CREATE OR REPLACE FUNCTION public.get_analytics_top_labels(
    start_year int DEFAULT NULL,
    end_year int DEFAULT NULL,
    limit_count int DEFAULT 10
)
RETURNS TABLE (label_name text, series_count bigint, episode_count bigint)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = ''
AS $$
    SELECT
        facts.label_name,
        count(DISTINCT facts.series_id)::bigint,
        count(*)::bigint
    FROM analytics.mart_episode_facts facts
    WHERE facts.label_name IS NOT NULL
      AND (start_year IS NULL OR facts.release_year >= start_year)
      AND (end_year IS NULL OR facts.release_year <= end_year)
    GROUP BY facts.label_name
    ORDER BY count(*) DESC, facts.label_name
    LIMIT greatest(1, least(coalesce(limit_count, 10), 50));
$$;

CREATE OR REPLACE FUNCTION public.get_analytics_top_speakers(
    start_year int DEFAULT NULL,
    end_year int DEFAULT NULL,
    limit_count int DEFAULT 10
)
RETURNS TABLE (
    speaker_name text,
    episode_count bigint,
    role_count bigint,
    credit_count bigint
)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = ''
AS $$
    SELECT
        credits.speaker_name,
        count(DISTINCT credits.episode_id)::bigint,
        count(DISTINCT credits.role_id)::bigint,
        count(*)::bigint
    FROM analytics.mart_speaker_credits credits
    WHERE (start_year IS NULL OR credits.release_year >= start_year)
      AND (end_year IS NULL OR credits.release_year <= end_year)
    GROUP BY credits.speaker_id, credits.speaker_name
    ORDER BY count(DISTINCT credits.episode_id) DESC, credits.speaker_name
    LIMIT greatest(1, least(coalesce(limit_count, 10), 50));
$$;

CREATE OR REPLACE FUNCTION public.get_analytics_duration_distribution(
    start_year int DEFAULT NULL,
    end_year int DEFAULT NULL
)
RETURNS TABLE (duration_bucket text, bucket_order int, episode_count bigint)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = ''
AS $$
    SELECT
        CASE
            WHEN facts.duration_minutes < 15 THEN '<15'
            WHEN facts.duration_minutes < 30 THEN '15–29'
            WHEN facts.duration_minutes < 45 THEN '30–44'
            WHEN facts.duration_minutes < 60 THEN '45–59'
            WHEN facts.duration_minutes < 90 THEN '60–89'
            ELSE '90+'
        END,
        CASE
            WHEN facts.duration_minutes < 15 THEN 1
            WHEN facts.duration_minutes < 30 THEN 2
            WHEN facts.duration_minutes < 45 THEN 3
            WHEN facts.duration_minutes < 60 THEN 4
            WHEN facts.duration_minutes < 90 THEN 5
            ELSE 6
        END,
        count(*)::bigint
    FROM analytics.mart_episode_facts facts
    WHERE facts.duration_minutes IS NOT NULL
      AND (start_year IS NULL OR facts.release_year >= start_year)
      AND (end_year IS NULL OR facts.release_year <= end_year)
    GROUP BY 1, 2
    ORDER BY 2;
$$;

CREATE OR REPLACE FUNCTION public.get_analytics_top_franchises(
    start_year int DEFAULT NULL,
    end_year int DEFAULT NULL,
    limit_count int DEFAULT 10
)
RETURNS TABLE (franchise_name text, series_count bigint, episode_count bigint)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = ''
AS $$
    SELECT
        facts.franchise_name,
        count(DISTINCT facts.series_id)::bigint,
        count(*)::bigint
    FROM analytics.mart_episode_facts facts
    WHERE (start_year IS NULL OR facts.release_year >= start_year)
      AND (end_year IS NULL OR facts.release_year <= end_year)
    GROUP BY facts.franchise_name
    ORDER BY count(*) DESC, facts.franchise_name
    LIMIT greatest(1, least(coalesce(limit_count, 10), 50));
$$;

REVOKE ALL ON FUNCTION public.get_analytics_kpis(int, int) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.get_analytics_episodes_per_year(int, int) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.get_analytics_genre_trends(int, int, int) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.get_analytics_top_labels(int, int, int) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.get_analytics_top_speakers(int, int, int) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.get_analytics_duration_distribution(int, int) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.get_analytics_top_franchises(int, int, int) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.get_analytics_kpis(int, int) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.get_analytics_episodes_per_year(int, int) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.get_analytics_genre_trends(int, int, int) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.get_analytics_top_labels(int, int, int) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.get_analytics_top_speakers(int, int, int) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.get_analytics_duration_distribution(int, int) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.get_analytics_top_franchises(int, int, int) TO anon, authenticated;
