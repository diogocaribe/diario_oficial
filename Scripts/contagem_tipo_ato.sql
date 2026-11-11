-- Contagem de atos por tipo (dominio.tipo_ato x processing.ato_tipo_ato).
-- Para rodar no DBeaver: posicione o cursor numa consulta e use Ctrl+Enter,
-- ou Alt+X para executar o script inteiro (cada consulta abre uma aba de resultado).
--
-- Um ato pode ter vários tipos, então a soma da coluna qtd_atos pode passar do
-- total de atos. Os vínculos só existem para publicações com auditoria IS TRUE
-- (gravados por `extrair-tipos-de-ato`).


-- 1) Quantidade de atos por tipo (inclui os tipos sem nenhum ato, com zero)
SELECT
    ta.id,
    ta.nome,
    ta.sigla,
    count(ata.ato_id)                  AS qtd_atos,
    count(DISTINCT a.publicacao_id)    AS qtd_publicacoes
FROM dominio.tipo_ato ta
LEFT JOIN processing.ato_tipo_ato ata ON ata.tipo_ato_id = ta.id
LEFT JOIN processing.ato a            ON a.id = ata.ato_id
GROUP BY ta.id, ta.nome, ta.sigla
ORDER BY qtd_atos DESC, ta.nome;


-- 2) Resumo: atos auditados com e sem tipo identificado
SELECT
    count(*)                                         AS atos_auditados,
    count(*) FILTER (WHERE t.ato_id IS NOT NULL)     AS atos_com_tipo,
    count(*) FILTER (WHERE t.ato_id IS NULL)         AS atos_sem_tipo
FROM processing.ato a
JOIN processing.publicacao p ON p.id = a.publicacao_id
LEFT JOIN (SELECT DISTINCT ato_id FROM processing.ato_tipo_ato) t ON t.ato_id = a.id
WHERE p.auditoria IS TRUE;


-- 3) Quantidade de atos por tipo e por mês da edição do DOE
SELECT
    date_trunc('month', d.dt_edicao)::date AS mes,
    ta.nome,
    ta.sigla,
    count(*)                               AS qtd_atos
FROM processing.ato_tipo_ato ata
JOIN dominio.tipo_ato ta      ON ta.id = ata.tipo_ato_id
JOIN processing.ato a         ON a.id = ata.ato_id
JOIN processing.publicacao p  ON p.id = a.publicacao_id
JOIN processing.doe_bruto d   ON d.id = p.doe_bruto_id
GROUP BY mes, ta.nome, ta.sigla
ORDER BY mes, qtd_atos DESC;
