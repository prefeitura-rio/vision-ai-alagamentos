
### GET IMAGES FROM DB

WITH cte AS (
  SELECT
    t1.id,
    t1.timestamp,
    t4.slug as object,
    t2.value as label,
    t3.public_url as snapshot_url
  FROM public.identification as t1
  JOIN public.label t2
    ON t1.label_id = t2.id
  JOIN public.snapshot t3
    ON t1.snapshot_id = t3.id
  JOIN public.object t4
    ON t2.object_id = t4.id
  LIMIT 10000
)
SELECT
  *
FROM cte
WHERE
  (object = 'road_blockade' OR object = 'water_level')
  AND (label = 'partially' OR label = 'totally' OR label = 'medium' OR label = 'high');
