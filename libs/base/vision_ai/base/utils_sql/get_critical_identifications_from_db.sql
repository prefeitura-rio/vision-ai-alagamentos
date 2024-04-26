WITH date_filtered AS (
    SELECT
        i.id,
        i."timestamp",
        i.label_id,
        i.snapshot_id
    FROM public.identification i
    WHERE i.timestamp >= '2024-03-21 00:00:00' AND i.timestamp <= '2024-03-24 23:59:59'
),
label_object_filtered AS (
    SELECT
        df.id AS identification_id,
        df."timestamp",
        df.snapshot_id,
        l.value AS label,
        o."name" AS object
    FROM date_filtered df
    LEFT JOIN public."label" l ON df.label_id = l.id
    LEFT JOIN public."object" o ON l.object_id = o.id
    WHERE o."name" = 'water_level' AND (l.value = 'medium' OR l.value = 'high')
)
SELECT
    lof.identification_id,
    h.id AS hide_identification,
    lof."timestamp",
    s.camera_id,
    lof.object,
    lof.label,
    i.label_explanation,
    s.public_url,
    c.latitude,
    c.longitude
  FROM label_object_filtered lof
  LEFT JOIN public.identification i ON lof.identification_id = i.id
  LEFT JOIN public."snapshot" s ON lof.snapshot_id = s.id
  LEFT JOIN public.camera c ON s.camera_id = c.id
  LEFT JOIN public.hide_identification h ON lof.identification_id = h.identification_id
ORDER BY lof."timestamp";