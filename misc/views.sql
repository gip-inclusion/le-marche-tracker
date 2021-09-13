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
