CREATE
OR replace VIEW public.trackers_v2 AS
SELECT
  trackers.id_internal,
  trackers.action,
  CASE
    WHEN ((trackers.data -> 'meta') ->> 'source') = 'symfony' THEN 'back_symfony'
    WHEN ((trackers.data -> 'meta') ->> 'source') = 'bitoubi_api' THEN 'back_django'
    WHEN ((trackers.data -> 'meta') ->> 'source') = 'bitoubi_frontend' THEN 'front'
    ELSE 'autre'
  END AS origin,
  CASE
    WHEN trackers.data -> 'meta' ->> 'user_type' IS NULL THEN 'anonyme'
    WHEN trackers.data -> 'meta' ->> 'user_type' = '4'
    OR trackers.data -> 'meta' ->> 'user_type' = 'SIAE' THEN 'structure inclusive'
    WHEN trackers.data -> 'meta' ->> 'user_type' = '6'
    OR trackers.data -> 'meta' ->> 'user_type' = 'PARTNER' THEN 'partenaire'
    WHEN trackers.data -> 'meta' ->> 'user_type' = '5'
    OR trackers.data -> 'meta' ->> 'user_type' = 'ADMIN' THEN 'administrateur'
    WHEN trackers.data -> 'meta' ->> 'user_type' = '3'
    OR trackers.data -> 'meta' ->> 'user_type' = 'BUYER' THEN 'acheteur'
    ELSE 'autre'
  END AS user_type,
  CASE
    WHEN trackers.data -> 'meta' ->> 'user_cookie_type' IS NULL THEN 'anonyme'
    WHEN trackers.data -> 'meta' ->> 'user_cookie_type' = 'actor' THEN 'acteur'
    WHEN trackers.data -> 'meta' ->> 'user_cookie_type' = 'buyer' THEN 'acheteur'
    WHEN trackers.data -> 'meta' ->> 'user_cookie_type' = 'siae' THEN 'structure'
    ELSE 'autre'
  END AS user_cookie_type,
  CASE
    WHEN action = 'click' THEN data -> 'meta' ->> 'id'
    ELSE ''
  END AS click_id,
  CASE
    WHEN action = 'click' THEN data -> 'meta' ->> 'href'
    ELSE ''
  END AS click_href,
  CASE
    WHEN action = 'directory_search' THEN jsonb_build_object(
      'searchType',
      data -> 'meta' -> 'searchType',
      'city',
      data -> 'meta' -> 'city',
      'department',
      data -> 'meta' -> 'department',
      'region',
      data -> 'meta' -> 'region',
      'sector',
      data -> 'meta' -> 'sector',
      'type',
      data -> 'meta' -> 'type',
      'prestaType',
      data -> 'meta' -> 'prestaType'
    )
    ELSE '"{}"'
  END AS search_request,
  CASE
    WHEN action = 'adopt' THEN data -> 'meta' ->> 'dir'
    ELSE NULL
  END AS adopted_structure,
  trackers.data ->> 'page' AS page,
  trackers.data ->> 'session_id' AS session_id,
  trackers.send_order AS "order",
  trackers.date_created,
  CASE
    WHEN trackers.data -> 'meta' ->> 'user_id' IS NULL THEN ''
    WHEN trackers.data -> 'meta' ->> 'user_id' != '' THEN trackers.data -> 'meta' ->> 'user_id'
    ELSE ''
  END AS user_id
FROM
  trackers
WHERE
  trackers.env = 'prod'
  AND trackers.isadmin = FALSE
  AND trackers.source = 'tracker'
