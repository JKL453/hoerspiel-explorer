-- ivfflat index for fast approximate nearest neighbor search
-- Requires maintenance_work_mem >= 64MB to build
-- Run: SET maintenance_work_mem = '64MB'; before executing if needed

SET maintenance_work_mem = '64MB';

CREATE INDEX ON episodes
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 50);