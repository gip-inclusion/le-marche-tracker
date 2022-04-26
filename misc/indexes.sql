CREATE INDEX ON trackers(env, isadmin, source);
CREATE INDEX ON trackers((data->'meta'->>'source')) WHERE data->'meta'->>'source' IS NOT NULL;
CREATE INDEX ON trackers((data->'meta'->>'user_type')) WHERE data->'meta'->>'user_type' IS NOT NULL;
CREATE INDEX ON trackers((data->'meta'->>'user_id'))  WHERE data->'meta'->>'user_id' IS NOT NULL;
CREATE INDEX ON trackers((data->'meta'->>'id'))  WHERE data->'meta'->>'id' IS NOT NULL;
CREATE INDEX ON trackers((data->>'session_id'))  WHERE data->>'session_id' IS NOT NULL;
