WITH parsed_ai_responses AS (
  SELECT
      camera_id,
      data_particao,
      start_datetime,
      end_datetime,
      error_step,
      error_name,
      error_message,
      JSON_EXTRACT_SCALAR(ai_input, '$.image_url') AS image_url,
      JSON_EXTRACT_SCALAR(ai_input, '$.snapshot_id') AS snapshot_id,
      JSON_EXTRACT_SCALAR(ai_input, '$.model') AS model,
      JSON_EXTRACT_SCALAR(ai_input, '$.max_output_tokens') AS max_output_tokens,
      JSON_EXTRACT_SCALAR(ai_input, '$.temperature') AS temperature,
      JSON_EXTRACT_SCALAR(ai_input, '$.top_k') AS top_k,
      JSON_EXTRACT_SCALAR(ai_input, '$.top_p') AS top_p,
      JSON_EXTRACT_SCALAR(ai_input, '$.object_ids') AS object_ids,
      JSON_EXTRACT_SCALAR(ai_input, '$.object_slugs') AS object_slugs,
      JSON_EXTRACT_SCALAR(ai_input, '$.prompt_text') AS prompt_text,
      JSON_EXTRACT_ARRAY(ai_response_parsed) AS ai_response_array
    FROM
      `rj-escritorio-dev.vision_ai.cameras_predicoes`
    WHERE data_particao = CURRENT_DATE("America/Sao_Paulo")
      AND start_datetime >= CAST(DATETIME_SUB(DATETIME(CURRENT_TIMESTAMP(), "America/Sao_Paulo"), INTERVAL 10 MINUTE) AS DATETIME)
),

unnested_responses AS (
  SELECT
    * EXCEPT (ai_response_array),
    JSON_EXTRACT_SCALAR(ai_response_parsed, '$.object') AS object,
    JSON_EXTRACT_SCALAR(ai_response_parsed, '$.label') AS label,
    JSON_EXTRACT_SCALAR(ai_response_parsed, '$.label_explanation') AS label_explanation,
    JSON_EXTRACT_SCALAR(ai_response_parsed, '$.api_status_code') AS api_status_code,
    JSON_EXTRACT_SCALAR(ai_response_parsed, '$.api_error_step') AS api_error_step,
    JSON_EXTRACT_SCALAR(ai_response_parsed, '$.api_error_name') AS api_error_name,
    JSON_EXTRACT_SCALAR(ai_response_parsed, '$.api_error_message') AS api_error_message,
  FROM
    parsed_ai_responses p
  CROSS JOIN
    UNNEST(p.ai_response_array) AS ai_response_parsed
)
SELECT
  * EXCEPT(ai_response_parsed)
FROM
  unnested_responses;
