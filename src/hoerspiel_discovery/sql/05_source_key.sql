BEGIN;

ALTER TABLE public.episodes
ADD COLUMN IF NOT EXISTS source_key TEXT;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM public.episodes LIMIT 1) THEN
        RAISE EXCEPTION
            'episodes must be empty before making source_key mandatory';
    END IF;
END
$$;

ALTER TABLE public.episodes
ALTER COLUMN source_key SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS episodes_source_key_key
ON public.episodes (source_key);

COMMIT;
