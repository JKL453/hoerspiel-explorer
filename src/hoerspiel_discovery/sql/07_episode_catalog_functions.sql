-- Run after a successful dbt build containing mart_series_episode_catalog.
-- These SECURITY DEFINER functions are the only browser-facing interface to
-- the categorized analytics catalog. Product tables remain unchanged.

CREATE OR REPLACE FUNCTION public.get_series_catalog_overview()
RETURNS TABLE (
    id bigint,
    name text,
    label text,
    episode_count bigint,
    category_counts jsonb
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
    SELECT
        counts.series_id,
        max(counts.series_name),
        max(counts.label_name),
        sum(counts.episode_count)::bigint,
        jsonb_agg(
            jsonb_build_object(
                'category_key', counts.category_key,
                'category_label', counts.category_label,
                'category_order', counts.category_order,
                'production_line_key', counts.production_line_key,
                'production_line_label', counts.production_line_label,
                'production_line_order', counts.production_line_order,
                'episode_count', counts.episode_count
            )
            ORDER BY counts.production_line_order, counts.category_order
        )
    FROM analytics.mart_series_category_counts counts
    GROUP BY counts.series_id
    ORDER BY sum(counts.episode_count) DESC, max(counts.series_name);
$$;

CREATE OR REPLACE FUNCTION public.get_series_catalog_facets(
    series_id_input bigint
)
RETURNS TABLE (
    production_line_key text,
    production_line_label text,
    production_line_order int,
    category_key text,
    category_label text,
    category_order int,
    episode_count bigint
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
    SELECT
        counts.production_line_key,
        counts.production_line_label,
        counts.production_line_order,
        counts.category_key,
        counts.category_label,
        counts.category_order,
        counts.episode_count
    FROM analytics.mart_series_category_counts counts
    WHERE counts.series_id = series_id_input
    ORDER BY counts.production_line_order, counts.category_order;
$$;

CREATE OR REPLACE FUNCTION public.get_series_episode_categories(
    series_id_input bigint
)
RETURNS TABLE (
    category_key text,
    category_label text,
    category_order int,
    episode_count bigint
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
    SELECT
        counts.category_key,
        counts.category_label,
        counts.category_order,
        sum(counts.episode_count)::bigint
    FROM analytics.mart_series_category_counts counts
    WHERE counts.series_id = series_id_input
    GROUP BY counts.category_key, counts.category_label, counts.category_order
    ORDER BY counts.category_order;
$$;

CREATE OR REPLACE FUNCTION public.get_series_episode_catalog(
    series_id_input bigint,
    category_key_input text DEFAULT NULL
)
RETURNS TABLE (
    id bigint,
    title text,
    episode_number bigint,
    description text,
    release_date date,
    duration_minutes double precision,
    cover_url text,
    category_key text,
    category_label text,
    variant_category text,
    edition_markers text
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
    SELECT
        catalog.episode_id,
        catalog.episode_title,
        catalog.episode_number,
        catalog.description,
        catalog.release_date,
        catalog.duration_minutes,
        catalog.cover_url,
        catalog.category_key,
        catalog.category_label,
        catalog.variant_category,
        catalog.edition_markers
    FROM analytics.mart_series_episode_catalog catalog
    WHERE catalog.series_id = series_id_input
      AND (category_key_input IS NULL OR catalog.category_key = category_key_input)
    ORDER BY
        catalog.category_order,
        catalog.episode_number NULLS LAST,
        catalog.release_date NULLS LAST,
        catalog.episode_id;
$$;

CREATE OR REPLACE FUNCTION public.get_series_episode_catalog(
    series_id_input bigint,
    category_key_input text,
    production_line_key_input text
)
RETURNS TABLE (
    id bigint,
    title text,
    episode_number bigint,
    description text,
    release_date date,
    duration_minutes double precision,
    cover_url text,
    category_key text,
    category_label text,
    variant_category text,
    edition_markers text
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
    SELECT
        catalog.episode_id,
        catalog.episode_title,
        catalog.episode_number,
        catalog.description,
        catalog.release_date,
        catalog.duration_minutes,
        catalog.cover_url,
        catalog.category_key,
        catalog.category_label,
        catalog.variant_category,
        catalog.edition_markers
    FROM analytics.mart_series_episode_catalog catalog
    WHERE catalog.series_id = series_id_input
      AND (category_key_input IS NULL OR catalog.category_key = category_key_input)
      AND (production_line_key_input IS NULL
        OR catalog.production_line_key = production_line_key_input)
    ORDER BY
        catalog.production_line_order,
        catalog.category_order,
        catalog.episode_number NULLS LAST,
        catalog.release_date NULLS LAST,
        catalog.episode_id;
$$;

REVOKE ALL ON FUNCTION public.get_series_catalog_overview() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.get_series_episode_categories(bigint) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.get_series_episode_catalog(bigint, text) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.get_series_catalog_facets(bigint) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.get_series_episode_catalog(bigint, text, text) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.get_series_catalog_overview() TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.get_series_episode_categories(bigint) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.get_series_episode_catalog(bigint, text) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.get_series_catalog_facets(bigint) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.get_series_episode_catalog(bigint, text, text) TO anon, authenticated;

-- Ensure PostgREST discovers new functions and overloads immediately.
NOTIFY pgrst, 'reload schema';
