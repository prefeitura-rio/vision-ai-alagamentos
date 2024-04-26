WITH
    historical_data AS (
        SELECT
            id_estacao,
            acumulado_chuva_30min AS acumulado_chuva,
            DATETIME(data_medicao) AS data_medicao,
            DATETIME(data_medicao) AS data_update,
            data_particao
        FROM `rj-cor.clima_pluviometro_staging.taxa_precipitacao_alertario_5min`
        WHERE data_particao BETWEEN '2024-03-21' AND '2024-03-24'
    ),

    last_measurements AS (
        SELECT
            id_estacao,
            data_update,
            data_medicao,
            "alertario" AS sistema,
            acumulado_chuva
        FROM historical_data
        WHERE acumulado_chuva IS NOT NULL
    ),

    intersected_areas AS (
        SELECT
            h3_grid.id,
            bairros.nome AS bairro,
            ST_CENTROID(h3_grid.geometry) AS geom,
            ST_AREA(ST_INTERSECTION(bairros.geometry, h3_grid.geometry)) AS intersection_area,
            ROW_NUMBER() OVER (PARTITION BY h3_grid.id ORDER BY ST_AREA(ST_INTERSECTION(bairros.geometry, h3_grid.geometry)) DESC) AS row_num
        FROM
            `rj-cor.dados_mestres.h3_grid_res8` h3_grid
            LEFT JOIN
            `rj-cor.dados_mestres.bairro` AS bairros
            ON ST_INTERSECTS(bairros.geometry, h3_grid.geometry)
        WHERE
            NOT ST_CONTAINS(ST_GEOGFROMTEXT('POLYGON((-43.35167114973923 -23.03719187431942, -43.21742224531541 -23.11411703410819, -43.05787930227852 -23.08560586153892, -43.13797293161925 -22.9854505090441, -43.24908435505957 -23.01309491285712, -43.29357259322761 -23.02302500142027, -43.35372293867113 -23.02286949608791, -43.35167114973923 -23.03719187431942))'), h3_grid.geometry)
            AND NOT ST_CONTAINS(ST_GEOGFROMTEXT('POLYGON((-43.17255470033881 -22.80357287766821, -43.16164114820394 -22.8246787848653, -43.1435175784006 -22.83820699694974, -43.08831858222521 -22.79901386772875, -43.09812065965735 -22.76990583135868, -43.11917632397501 -22.77502040608505, -43.12252626904735 -22.74275730775724, -43.13510053525226 -22.7443347361711, -43.1568784870256 -22.79110122556994, -43.17255470033881 -22.80357287766821))'), h3_grid.geometry)
            AND h3_grid.id NOT IN ("88a8a06a31fffff", "88a8a069b5fffff", "88a8a3d357fffff", "88a8a3d355fffff", "88a8a068adfffff", "88a8a06991fffff", "88a8a06999fffff")
    ),

    h3_chuvas AS (
        SELECT
            h3.*,
            lm.data_medicao,
            lm.id_estacao,
            CAST(lm.acumulado_chuva AS FLOAT64) AS acumulado_chuva,
            CAST(lm.acumulado_chuva AS FLOAT64) / power(h3.dist, 5) AS p1_15min,
            1 / power(h3.dist, 5) AS inv_dist
        FROM (
            WITH centroid_h3 AS (
                SELECT
                    *
                FROM intersected_areas
                WHERE row_num = 1
            ),
            estacoes_pluviometricas AS (
                SELECT
                    id_estacao AS id,
                    estacao,
                    "alertario" AS sistema,
                    ST_GEOGPOINT(CAST(longitude AS FLOAT64), CAST(latitude AS FLOAT64)) AS geom
                FROM `rj-cor.clima_pluviometro.estacoes_alertario`
            ),
            estacoes_mais_proximas AS (
                SELECT AS VALUE s
                FROM (
                    SELECT
                        ARRAY_AGG(
                            STRUCT<id_h3 STRING, id_estacao STRING, estacao STRING, bairro STRING, dist FLOAT64, sistema STRING>(
                                a.id, b.id, b.estacao, a.bairro,
                                ST_DISTANCE(a.geom, b.geom),
                                b.sistema
                            )
                            ORDER BY ST_DISTANCE(a.geom, b.geom)
                        ) AS ar
                    FROM (SELECT id, geom, bairro FROM centroid_h3) a
                    CROSS JOIN(
                        SELECT id, estacao, sistema, geom
                        FROM estacoes_pluviometricas
                        WHERE geom IS NOT NULL
                    ) b
                WHERE a.id <> b.id
                GROUP BY a.id
                ) ab
                CROSS JOIN UNNEST(ab.ar) s
            )
            SELECT
                *,
                ROW_NUMBER() OVER (PARTITION BY id_h3 ORDER BY dist) AS ranking
            FROM estacoes_mais_proximas
            ORDER BY id_h3, ranking
        ) h3
        LEFT JOIN last_measurements lm
            ON lm.id_estacao = h3.id_estacao AND lm.sistema = h3.sistema
    ),

    aggregated_data AS (
        SELECT
            id_h3,
            bairro,
            SUM(p1_15min) / SUM(inv_dist) AS qnt_chuva,
            STRING_AGG(estacao ORDER BY estacao) AS estacoes,
            data_medicao
        FROM h3_chuvas
        GROUP BY id_h3, bairro, data_medicao
    ),

    final_table AS (
        SELECT
            id_h3,
            bairro,
            CAST(ROUND(qnt_chuva, 2) AS DECIMAL) AS qnt_chuva,
            estacoes,
            data_medicao,
            CASE
                WHEN qnt_chuva > 2 * 0 AND qnt_chuva <= 2 * 1.25 THEN 'chuva fraca'
                WHEN qnt_chuva > 2 * 1.25 AND qnt_chuva <= 2 * 6.25 THEN 'chuva moderada'
                WHEN qnt_chuva > 2 * 6.25 AND qnt_chuva <= 2 * 12.5 THEN 'chuva forte'
                WHEN qnt_chuva > 2 * 12.5 THEN 'chuva muito forte'
                ELSE 'sem chuva'
            END AS status,
            CASE
                WHEN qnt_chuva > 2 * 0 AND qnt_chuva <= 2 * 1.25 THEN '#DAECFB'
                WHEN qnt_chuva > 2 * 1.25 AND qnt_chuva <= 2 * 6.25 THEN '#A9CBE8'
                WHEN qnt_chuva > 2 * 6.25 AND qnt_chuva <= 2 * 12.5 THEN '#77A9D5'
                WHEN qnt_chuva > 2 * 12.5 THEN '#125999'
                ELSE '#ffffff'
            END AS color
        FROM aggregated_data
    )

SELECT
    id_h3,
    bairro,
    COALESCE(qnt_chuva, 0) AS quantidade,
    estacoes,
    status,
    color,
    data_medicao
FROM final_table