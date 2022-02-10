CREATE OR replace VIEW public.trackers_v1
AS
  SELECT trackers.id_internal,
         trackers.action,
         CASE WHEN ( ( trackers.data -> 'meta' ) ->> 'source' ) = 'symfony' THEN 'back'
           ELSE 'front'
         END                            AS origin,
         CASE
           WHEN trackers.data -> 'meta' ->> 'user_type' IS NULL THEN 'anonyme'
           WHEN trackers.data -> 'meta' ->> 'user_type' = '4' THEN 'structure inclusive'
           WHEN trackers.data -> 'meta' ->> 'user_type' = '6' THEN 'partenaire'
           WHEN trackers.data -> 'meta' ->> 'user_type' = '5' THEN 'administrateur'
           WHEN trackers.data -> 'meta' ->> 'user_type' = '3' THEN 'acheteur'
           ELSE 'autre'
         END                            AS user_type,
         trackers.data ->> 'page'       AS page,
         trackers.data ->> 'session_id' AS session_id,
         trackers.send_order            AS "order",
         trackers.date_created
  FROM   trackers
  WHERE  trackers.env = 'prod'
         AND trackers.isadmin = FALSE
         AND trackers.source = 'tracker'



CREATE OR replace VIEW public.trackers_v2
AS
  SELECT trackers.id_internal,
         trackers.action,
         CASE
          WHEN ( ( trackers.data -> 'meta' ) ->> 'source' ) = 'symfony' THEN 'back_symfony'
          WHEN ( ( trackers.data -> 'meta' ) ->> 'source' ) = 'bitoubi_api' THEN 'back_django'
           ELSE 'front'
         END                            AS origin,
         CASE
           WHEN trackers.data -> 'meta' ->> 'user_type' IS NULL THEN 'anonyme'
           WHEN trackers.data -> 'meta' ->> 'user_type' = '4' THEN 'structure inclusive'
           WHEN trackers.data -> 'meta' ->> 'user_type' = '6' THEN 'partenaire'
           WHEN trackers.data -> 'meta' ->> 'user_type' = '5' THEN 'administrateur'
           WHEN trackers.data -> 'meta' ->> 'user_type' = '3' THEN 'acheteur'
           ELSE 'autre'
         END                            AS user_type,
         CASE
           WHEN trackers.data -> 'meta' ->> 'user_cookie_type' IS NULL THEN 'anonyme'
           WHEN trackers.data -> 'meta' ->> 'user_cookie_type' = 'actor' THEN 'acteur'
           WHEN trackers.data -> 'meta' ->> 'user_cookie_type' = 'buyer' THEN 'acheteur'
           WHEN trackers.data -> 'meta' ->> 'user_cookie_type' = 'siae' THEN 'structure'
           ELSE 'autre'
         END                            AS user_cookie_type,
         CASE
           WHEN action = 'click' THEN data->'meta'->>'id'
           ELSE ''
         END                            AS click_id,
         CASE
           WHEN action = 'click' THEN data->'meta'->>'href'
           ELSE ''
         END                            AS click_href,
         CASE
           WHEN trackers.data -> 'meta' ->> 'user_email' IS NULL THEN ''
           WHEN trackers.data -> 'meta' ->> 'user_email' != '' THEN trackers.data -> 'meta' ->> 'user_email'
           ELSE ''
         END                            AS user_email,
         CASE
           WHEN action = 'directory_search' THEN jsonb_build_object(
            'searchType', data->'meta'->'searchType',
            'city', data->'meta'->'city',
            'department', data->'meta'->'department',
            'region', data->'meta'->'region',
            'sector', data->'meta'->'sector',
            'type', data->'meta'->'type',
            'prestaType', data->'meta'->'prestaType')
           ELSE  '"{}"'
         END                            AS search_request,
         CASE
           WHEN action = 'adopt' THEN data->'meta'->>'dir'
           ELSE NULL
         END                            AS adopted_structure,
         trackers.data ->> 'page'       AS page,
         trackers.data ->> 'session_id' AS session_id,
         trackers.send_order            AS "order",
         trackers.date_created
  FROM   trackers
WHERE  trackers.env = 'prod'
AND trackers.isadmin = FALSE
AND trackers.source = 'tracker'

CREATE INDEX ON trackers(env, isadmin, source);
CREATE INDEX ON trackers((data->'meta'->>'source')) WHERE data->'meta'->>'source' IS NOT NULL;
CREATE INDEX ON trackers((data->'meta'->>'user_type')) WHERE data->'meta'->>'user_type' IS NOT NULL;
CREATE INDEX ON trackers((data->'meta'->>'user_email'))  WHERE data->'meta'->>'user_email' IS NOT NULL;
CREATE INDEX ON trackers((data->'meta'->>'user_cookie_type'))  WHERE data->'meta'->>'user_cookie_type' IS NOT NULL;
CREATE INDEX ON trackers((data->'meta'->>'id'))  WHERE data->'meta'->>'id' IS NOT NULL;
CREATE INDEX ON trackers((data->>'session_id'))  WHERE data->>'session_id' IS NOT NULL;

