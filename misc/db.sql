-- Schema for a simple tracking table
CREATE TABLE trackers (
    id_internal SERIAL PRIMARY KEY,
    version INT NOT NULL,
    date_created TIMESTAMP WITH TIME ZONE DEFAULT now(),
    send_order INT,

    session_id UUID NOT NULL,
    env TEXT NOT NULL,
    source TEXT NOT NULL,
    page TEXT,
    action TEXT,
    data JSONB
);
CREATE INDEX idx_trackers_sid ON trackers USING BTREE (session_id);
CREATE INDEX idx_trackers_created ON trackers USING BTREE (date_created);
CREATE INDEX idx_trackers_env ON trackers USING BTREE (env);
CREATE INDEX idx_trackers_source ON trackers USING BTREE (source);

-- Indices for generic metabase views
CREATE INDEX idx_trackers_page ON trackers USING BTREE (page) WHERE page IS NOT NULL;
CREATE INDEX idx_trackers_action ON trackers USING BTREE (action) WHERE action IS NOT NULL;
