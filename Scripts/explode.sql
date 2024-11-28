WITH poder AS (
  -- Extrai as chaves do primeiro nível (por exemplo, "EXECUTIVO")
  SELECT
      id AS doe_bruto_id,
      jsonb_object_keys(doe_json) AS poder,
      doe_json -> jsonb_object_keys(doe_json) AS _json
  FROM processing.doe_bruto
  WHERE dt_edicao = '2024-02-09'
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
				jsonb_typeof(_json) = 'object' THEN _json
		 END AS _json,
		 CASE 
			WHEN 
				jsonb_typeof(_json) = 'array' THEN _json
		 END AS conteudo
     FROM divisao_adm_direta_
),
tratanto_divisao_adm_indireta AS (
	SELECT 
		doe_bruto_id,
	    poder,
        adm_direta,
        divisao_adm_direta,
        adm_indireta,
		CASE 
			WHEN divisao_adm_indireta IN (SELECT dai.nome FROM dominio.divisao_adm_indireta dai) THEN divisao_adm_indireta
		END AS divisao_adm_indireta,
        _json
	FROM (	
		SELECT
			doe_bruto_id,
		    poder,
	        adm_direta,
	        divisao_adm_direta,
	        adm_indireta,
	        jsonb_object_keys(_json) AS divisao_adm_indireta,
	        _json -> jsonb_object_keys(_json) AS _json     
		FROM tratando_divisao_adm_direta
	) t
	WHERE divisao_adm_indireta IN (SELECT nome FROM dominio.divisao_adm_indireta dai)
),
tratanto_divisao_adm_indireta_ AS (
	SELECT
		doe_bruto_id,
	    poder,
        adm_direta,
        divisao_adm_direta,
        adm_indireta,
        divisao_adm_indireta,
		jsonb_object_keys(_json) AS tipo_publicacao,
		_json -> jsonb_object_keys(_json) AS _json 
	FROM tratanto_divisao_adm_indireta
)
--Administracao Direta
SELECT
	doe_bruto_id,
	p.id AS poder_id,
	ad.id AS adm_direta_id,
	dad.id AS divisao_adm_direta_id,
	ai.id AS adm_indireta_id,
	NULL AS divisao_adm_indireta,
	tp.id AS tipo_publicacao_id,
	jsonb_array_elements_text(conteudo)::jsonb->>'nome' AS nome_ato,
	jsonb_array_elements_text(conteudo)::jsonb->>'identificador' AS identificador_link,
	jsonb_array_elements_text(conteudo)::jsonb->>'link' AS link
FROM tratando_divisao_adm_direta
LEFT JOIN dominio.poder p ON p.nome = poder
LEFT JOIN dominio.adm_direta ad ON ad.nome = adm_direta
LEFT JOIN dominio.divisao_adm_direta dad ON dad.nome = divisao_adm_direta
LEFT JOIN dominio.adm_indireta ai ON ai.nome = adm_indireta
LEFT JOIN dominio.tipo_publicacao tp ON tp.nome = tipo_publicacao
UNION
-- Administracao Indireta com 4 niveis
SELECT 
	doe_bruto_id,
	poder_id,
    adm_direta_id,
    divisao_adm_direta_id,
    adm_indireta_id,
    divisao_adm_indireta,
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
	    NULL::NUMERIC AS divisao_adm_indireta,
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
LEFT JOIN dominio.tipo_publicacao tp2 ON tp2.nome = t.tipo_publicacao
-- Administracao Indireta com 5 niveis
UNION
SELECT
	doe_bruto_id,
    p.id  AS poder_id,
    ad.id AS adm_direta_id,
    dad.id AS divisao_adm_direta_id,
    ai.id AS adm_indireta_id,
    dai.id AS divisao_adm_indireta,
	tp.id AS tipo_publicacao_id,
	jsonb_array_elements_text(_json)::jsonb->>'nome' AS nome_ato,
	jsonb_array_elements_text(_json)::jsonb->>'identificador' AS identificador_link,
	jsonb_array_elements_text(_json)::jsonb->>'link' AS link
FROM tratanto_divisao_adm_indireta_
LEFT JOIN dominio.poder p ON p.nome = poder
LEFT JOIN dominio.adm_direta ad ON ad.nome = adm_direta
LEFT JOIN dominio.divisao_adm_direta dad ON dad.nome = divisao_adm_direta
LEFT JOIN dominio.adm_indireta ai ON ai.nome = adm_indireta
LEFT JOIN dominio.divisao_adm_indireta dai ON dai.nome = divisao_adm_indireta
LEFT JOIN dominio.tipo_publicacao tp ON tp.nome = tipo_publicacao;


-- Consulta para fazer o join dos atributos de publicacao
SELECT p.id, db.nro_edicao, db.dt_edicao, p2.nome AS poder, ad.nome AS adm_direta, ai.nome AS adm_indireta, dad.nome AS divisao_adm_direta, tp.nome AS tipo_publicacao, 
		p.nome_ato, p.identificador_link, p.link  
FROM processing.doe_bruto db 
JOIN processing.publicacao p ON p.doe_bruto_id = db.id 
LEFT JOIN dominio.poder p2 ON p.poder_id = p2.id 
LEFT JOIN dominio.adm_direta ad ON p.adm_direta_id = ad.id
LEFT JOIN dominio.adm_indireta ai ON p.adm_indireta_id = ai.id
LEFT JOIN dominio.divisao_adm_direta dad ON p.divisao_adm_direta_id = dad.id
LEFT JOIN dominio.tipo_publicacao tp ON p.tipo_publicacao_id = tp.id


DELETE FROM processing.ato;
SELECT setval('processing.ato_id_seq', 1, false);

DELETE FROM processing.publicacao;
DELETE FROM processing.doe_bruto; 

SELECT count(*) FROM processing.ato;


