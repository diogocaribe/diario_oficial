  WITH json_keys AS (
      -- Extrai as chaves do primeiro nível (por exemplo, "EXECUTIVO")
      SELECT
          nro_edicao,
          jsonb_object_keys(doe_json) AS poder_key,
          doe_json -> jsonb_object_keys(doe_json) AS poder_json
      FROM processing.doe_bruto
      --WHERE dt_edicao = '{data}'
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
      nro_edicao AS doe_nro_edicao,
      (SELECT id FROM dominio.poder p WHERE p.nome = poder_key) AS poder_id,
      (SELECT id FROM dominio.adm_direta ad WHERE ad.nome = adm_direta_key) AS adm_direta_id,
      (SELECT id FROM dominio.divisao_adm_direta dad WHERE diretoria_key IN (SELECT dad.nome FROM dominio.divisao_adm_direta dad)) AS divisao_adm_direta_id,
      (SELECT id FROM dominio.adm_indireta ai WHERE diretoria_key IN (SELECT ai.nome FROM dominio.adm_indireta dad1)) AS adm_indireta_id,
      portaria ->> 'nome' AS nome_ato,
      portaria ->> 'identificador' AS identificador_link,
      portaria ->> 'link' AS link
  FROM expanded_portarias;
  -- Rodar para ver o resultado em alfanumerico
  -- SELECT
  --    nro_edicao,
  --    poder_key AS poder,
  --    adm_direta_key AS adm_direta,
  --    CASE
  --       WHEN diretoria_key IN (SELECT dad.nome FROM dominio.divisao_adm_direta dad) THEN diretoria_key
  --    END AS divisao_adm_direta,
  --    CASE
  --        WHEN diretoria_key IN (SELECT ai.nome FROM dominio.adm_indireta ai) THEN diretoria_key
  --    END AS divisao_adm_direta,
  --    portaria ->> 'nome' AS nome,
  --    portaria ->> 'identificador' AS identificador,
  --    portaria ->> 'link' AS link
  -- FROM expanded_portarias;
 
 INSERT INTO processing.publicacao (
    doe_nro_edicao,
    poder_id,
    adm_direta_id,
    adm_indireta_id,
    divisao_adm_direta_id,
    nome_ato,
    identificador_link,
    link
) VALUES (
    23822,
    1,
    1,
    1,
    NULL,  -- Para divisao_adm_direta_id, que é NULL
    '#879701 - Integracao_RHBAHIA_Z500738863_202402700033',
    '951087',
    'https://dool.egba.ba.gov.br/apifront/portal/edicoes/publicacoes_ver_conteudo/951087'
);


