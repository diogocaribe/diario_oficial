-- Consulta para administracao direta
WITH poder AS (
    -- Extrai as chaves do primeiro nível (por exemplo, "EXECUTIVO")
    SELECT
        id AS doe_bruto_id,
        jsonb_object_keys(doe_json) AS poder,
        doe_json -> jsonb_object_keys(doe_json) AS _json
    FROM processing.doe_bruto
    WHERE dt_edicao = '2024-01-06'
),
adm_direta AS (
    -- Extrai as chaves do segundo nível a partir do resultado da CTE anterior
    SELECT
    	doe_bruto_id,
        poder,
        jsonb_object_keys(_json) AS adm_direta,
        _json -> jsonb_object_keys(_json) AS _json
    FROM poder
),
divisao_adm_direta_ AS (
    -- Extrai as chaves do segundo nível a partir do resultado da CTE anterior
    SELECT
		doe_bruto_id,
        poder,
        adm_direta,
        jsonb_object_keys(_json) AS divisao_adm_direta,
        _json -> jsonb_object_keys(_json) AS _json
    FROM adm_direta
),
tratando_divisao_adm_direta AS (
	SELECT
		doe_bruto_id,
        poder,
        adm_direta,
        CASE 
        	WHEN divisao_adm_direta IN (SELECT dad.nome FROM dominio.divisao_adm_direta dad) THEN divisao_adm_direta
        END AS divisao_adm_direta,
        CASE 
        	WHEN divisao_adm_direta IN (SELECT ai.nome FROM dominio.adm_indireta ai) THEN divisao_adm_direta
        END AS adm_indireta,
        CASE 
        	WHEN divisao_adm_direta IN (SELECT tp.nome FROM dominio.tipo_publicacao tp) THEN divisao_adm_direta
        END AS tipo_publicacao,
        CASE 
        	WHEN
	        	jsonb_typeof(_json) = 'array' THEN _json
	        ELSE
	        	_json
        END AS _json
    FROM divisao_adm_direta_
)
--Administracao Direta
SELECT
	doe_bruto_id,
	p.id AS poder_id,
    ad.id AS adm_direta_id,
	dad.id AS divisao_adm_direta_id,
	ai.id AS adm_indireta_id,
	tp.id AS tipo_publicacao_id,
	jsonb_array_elements_text(_json)::jsonb->>'nome' AS nome_ato,
	jsonb_array_elements_text(_json)::jsonb->>'identificador' AS identificador_link,
	jsonb_array_elements_text(_json)::jsonb->>'link' AS link 
FROM tratando_divisao_adm_direta
LEFT JOIN dominio.poder p ON p.nome = poder
LEFT JOIN dominio.adm_direta ad ON ad.nome = adm_direta
LEFT JOIN dominio.divisao_adm_direta dad ON dad.nome = divisao_adm_direta
LEFT JOIN dominio.adm_indireta ai ON ai.nome = adm_indireta
LEFT JOIN dominio.tipo_publicacao tp ON tp.nome = tipo_publicacao
WHERE jsonb_typeof(_json) = 'array'
UNION
-- Administracao Indireta
SELECT 
	doe_bruto_id,
	poder_id,
    adm_direta_id,
    divisao_adm_direta_id,
    adm_indireta_id,
	tp2.id AS tipo_publicacao_id,
	t.nome AS nome_ato, 
	identificador AS identificador_link, 
	link
FROM (
	SELECT 
		doe_bruto_id,
		p.id AS poder_id,
	    ad.id AS adm_direta_id,
	    dad.id AS divisao_adm_direta_id,
	    ai.id AS adm_indireta_id,
	    jsonb_object_keys(_json) AS tipo_publicacao,
	    jsonb_array_elements_text(_json -> jsonb_object_keys(_json))::jsonb->>'nome' AS nome,
	    jsonb_array_elements_text(_json -> jsonb_object_keys(_json))::jsonb->>'identificador' AS identificador,
	    jsonb_array_elements_text(_json -> jsonb_object_keys(_json))::jsonb->>'link' AS link
	FROM tratando_divisao_adm_direta
	LEFT JOIN dominio.poder p ON p.nome = poder
	LEFT JOIN dominio.adm_direta ad ON ad.nome = adm_direta
	LEFT JOIN dominio.divisao_adm_direta dad ON dad.nome = divisao_adm_direta
	LEFT JOIN dominio.adm_indireta ai ON ai.nome = adm_indireta
	LEFT JOIN dominio.tipo_publicacao tp ON tp.nome = tipo_publicacao
	WHERE jsonb_typeof(_json) = 'object'
) t
LEFT JOIN dominio.tipo_publicacao tp2 ON tp2.nome = t.tipo_publicacao;