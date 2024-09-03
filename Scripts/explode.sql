WITH json_keys AS (
    -- Extrai as chaves do primeiro nível (por exemplo, "EXECUTIVO")
    SELECT
        nro_edicao,
        jsonb_object_keys(doe_json) AS poder_key,
        doe_json -> jsonb_object_keys(doe_json) AS poder_json
    FROM processing.doe_bruto
    WHERE dt_edicao = '2024-01-23'
),
adm_direta_keys AS (
    -- Extrai as chaves do segundo nível a partir do resultado da CTE anterior
    SELECT
        nro_edicao,
        poder_key,
        jsonb_object_keys(poder_json) AS adm_direta_key,
        poder_json -> jsonb_object_keys(poder_json) AS adm_direta_json
    FROM json_keys
),
diretorias AS (
    -- Extrai as chaves do terceiro nível a partir do resultado da CTE anterior
    SELECT
        nro_edicao,
        poder_key,
        adm_direta_key,
        jsonb_object_keys(adm_direta_json) AS diretoria_key,
        adm_direta_json -> jsonb_object_keys(adm_direta_json) AS diretoria_json
    FROM adm_direta_keys
),
portarias AS (
    -- Extrai a lista de portarias a partir do resultado da CTE anterior
    SELECT
        nro_edicao,
        poder_key,
        adm_direta_key,
        diretoria_key,
        (diretoria_json -> 'Portarias') AS portarias_array
    FROM diretorias
),
expanded_portarias AS (
    -- Expande a lista de portarias em linhas e extrai os campos desejados
    SELECT
        nro_edicao,
        poder_key,
        adm_direta_key,
        diretoria_key,
        jsonb_array_elements(portarias_array) AS portaria
    FROM portarias
)
-- Consulta final para selecionar os campos específicos das portarias
SELECT
    nro_edicao,
    poder_key AS poder,
    adm_direta_key AS adm_direta,
    CASE 
    	WHEN diretoria_key IN (SELECT dad.nome FROM dominio.divisao_adm_direta dad) THEN diretoria_key
    END AS divisao_adm_direta,
  	CASE 
    	WHEN diretoria_key IN (SELECT ai.nome FROM dominio.adm_indireta ai) THEN diretoria_key
    END AS divisao_adm_direta,
    portaria ->> 'nome' AS nome,
    portaria ->> 'identificador' AS identificador,
    portaria ->> 'link' AS link
FROM expanded_portarias;
