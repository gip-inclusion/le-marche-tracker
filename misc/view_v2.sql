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
    WHEN ((trackers.data -> 'meta') ->> 'user_type') IS NULL
      THEN 'anonyme'
    WHEN ((trackers.data -> 'meta') ->> 'user_type') = '4'
      OR ((trackers.data -> 'meta') ->> 'user_type') = 'SIAE'
      THEN 'structure inclusive'
    WHEN ((trackers.data -> 'meta') ->> 'user_type') = '6'
      OR ((trackers.data -> 'meta') ->> 'user_type') = 'PARTNER'
      THEN 'partenaire'
    WHEN ((trackers.data -> 'meta') ->> 'user_type') = '5'
      OR ((trackers.data -> 'meta') ->> 'user_type') = 'ADMIN'
      THEN 'administrateur'
    WHEN ((trackers.data -> 'meta') ->> 'user_type') = '3'
      OR ((trackers.data -> 'meta') ->> 'user_type') = 'BUYER'
      THEN 'acheteur'
    ELSE 'autre'
  END AS user_type,
  CASE
    WHEN ((trackers.data -> 'meta') ->> 'user_cookie_type') IS NULL THEN 'anonyme'
    WHEN ((trackers.data -> 'meta') ->> 'user_cookie_type') = 'actor' THEN 'acteur'
    WHEN ((trackers.data -> 'meta') ->> 'user_cookie_type') = 'buyer' THEN 'acheteur'
    WHEN ((trackers.data -> 'meta') ->> 'user_cookie_type') = 'siae' THEN 'structure'
    ELSE 'autre'
  END AS user_cookie_type,
  CASE
    WHEN trackers.action = 'click' THEN (trackers.data -> 'meta') ->> 'id'
    ELSE ''
  END AS click_id,
  CASE
      WHEN trackers.action = 'click' THEN (trackers.data -> 'meta') ->> 'href'
      ELSE ''
  END AS click_href,
  CASE
    WHEN trackers.action = 'directory_search' THEN jsonb_build_object(
      'searchType', (trackers.data -> 'meta') ->> 'searchType',
      'city', (trackers.data -> 'meta') ->> 'city',
      'department', (trackers.data -> 'meta') ->> 'department',
      'region', (trackers.data -> 'meta') ->> 'region',
      'sector', (trackers.data -> 'meta') ->> 'sectors',
      'perimeters', (trackers.data -> 'meta') ->> 'perimeters',
      'type', (trackers.data -> 'meta') ->> 'type',
      'prestaType', (trackers.data -> 'meta') ->> 'prestaType',
      'siaes_kind', (trackers.data -> 'meta') ->> 'kind',
      'results_count', (trackers.data -> 'meta') ->> 'results_count')
    ELSE '"{}"'::jsonb
  END AS search_request,
  CASE
      WHEN trackers.action = 'adopt' THEN (trackers.data -> 'meta') ->> 'dir'
      ELSE NULL
  END AS adopted_structure,
  trackers.data ->> 'page' AS page,
  trackers.date_created,
  CASE
      WHEN ((trackers.data -> 'meta') ->> 'user_id') IS NULL THEN NULL::integer
      WHEN ((trackers.data -> 'meta') ->> 'user_id') <> '' THEN ((trackers.data -> 'meta') ->> 'user_id')::integer
      ELSE NULL::integer
  END AS user_id
FROM
  trackers
WHERE
  trackers.env = 'prod'
  AND trackers.isadmin in (false, NULL)
  AND trackers.source = 'tracker';
