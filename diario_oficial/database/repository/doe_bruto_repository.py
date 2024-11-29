from database.configs.connection import DBConnectionHandler
from database.entity.doe_bruto import DiarioOficialBruto

from sqlalchemy.exc import IntegrityError
from psycopg import errors


from datetime import datetime

from sqlalchemy import text


class DiarioOficialBrutoRepository:
    def check_if_date_doe_coleted(self, data: datetime.date):
        """Verificar se o diario oficial daquela data foi coletado

        Raises:
            exception: _description_

        Returns:
            _type_: _description_
        """
        with DBConnectionHandler() as db:
            try:
                result = (
                    db.session.query(DiarioOficialBruto)
                    .filter(DiarioOficialBruto.dt_edicao == data)
                    .first()
                )
                return result
            except Exception as exception:
                raise exception

    def save_data(self, **kwargs):
        """Inserindo os dados coletados do diario oficial

        Raises:
            exception: _description_
        """
        with DBConnectionHandler() as db:
            try:
                dados = DiarioOficialBruto(**kwargs)
                db.session.add(dados)
                db.session.commit()
                print('Dados brutos salvos.')
            except IntegrityError as e:
                # Verifica se a causa foi uma violação de unicidade
                if isinstance(e.orig, errors.UniqueViolation):
                    print('Erro: Dados brutos já coletado.')
                    db.session.rollback()  # Reverte a transação
                else:
                    print(f'Outro erro de integridade: {e}')
                    db.session.rollback()
            except Exception as exception:
                db.session.rollback()
                raise exception

    def explodir_doe_bruto_json(self, data: datetime.date):
        """Verificar se o diario oficial daquela data foi coletado

        Raises:
            exception: _description_

        Returns:
            _type_: _description_
        """
        with DBConnectionHandler() as db:
            try:
                sql = f"""
               WITH poder AS (
                -- Extrai as chaves do primeiro nível (por exemplo, "EXECUTIVO")
                SELECT
                    id AS doe_bruto_id,
                    jsonb_object_keys(doe_json) AS poder,
                    doe_json -> jsonb_object_keys(doe_json) AS _json
                FROM processing.doe_bruto
                WHERE dt_edicao = '{data}'
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
                """

                nivel_4 = """
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
                """
                nivel_5 = """
                -- Administracao Indireta com 4 niveis
                -- Administracao Indireta com 5 niveis
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
                LEFT JOIN dominio.tipo_publicacao tp ON tp.nome = tipo_publicacao
                """

                sql = sql + nivel_4

                try:
                    result = db.get_engine().connect().execute(text(sql))
                    columns = result.keys()
                    # Converter os resultados para uma lista de dicionários
                    result = [dict(zip(columns, row)) for row in result.fetchall()]
                except Exception as e:
                    print('Extraindo nivel 5')
                    sql = f"""
                    WITH poder AS (
                    -- Extrai as chaves do primeiro nível (por exemplo, "EXECUTIVO")
                    SELECT
                        id AS doe_bruto_id,
                        jsonb_object_keys(doe_json) AS poder,
                        doe_json -> jsonb_object_keys(doe_json) AS _json
                    FROM processing.doe_bruto
                    WHERE dt_edicao = '{data}'
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
                    """
                    result = db.get_engine().connect().execute(text(sql))
                    columns = result.keys()
                    # Converter os resultados para uma lista de dicionários
                    result = [dict(zip(columns, row)) for row in result.fetchall()]
                return result
            except Exception as exception:
                raise exception

    def update_doe_bruto_para_publicacao(self, id_doe: int):
        """Realizar o update quando o processamento do doe_bruto for realizado.
        Este processamento pega o json do doe e separa os links na tabela de publicacao

        Args:
            id_doe (int): id do doe_bruto que será atualizado

        Raises:
            exception: _description_
        """
        with DBConnectionHandler() as db:
            try:
                objeto = (
                    db.session.query(DiarioOficialBruto)
                    .filter(DiarioOficialBruto.id == id_doe)
                    .one()
                )
                objeto.doe_bruto_para_publicacao = True
                # Commit a transação
                db.session.commit()
            except Exception as exception:
                db.session.rollback()
                raise exception
