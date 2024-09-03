import json
from database.configs.connection import DBConnectionHandler
from database.entity.doe_bruto import DiarioOficialBruto
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
                db.session.rollback()
                raise exception

    def save_data(self, **kwargs):
        with DBConnectionHandler() as db:
            try:
                dados = DiarioOficialBruto(**kwargs)
                db.session.add(dados)
                db.session.commit()
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
                    WITH json_keys AS (
                        -- Extrai as chaves do primeiro nível (por exemplo, "EXECUTIVO")
                        SELECT
                            nro_edicao,
                            jsonb_object_keys(doe_json) AS poder_key,
                            doe_json -> jsonb_object_keys(doe_json) AS poder_json
                        FROM processing.doe_bruto
                        WHERE dt_edicao = '{data}'
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
                """
                result = db.get_engine().connect().execute(text(sql))
                columns = result.keys()
                # Converter os resultados para uma lista de dicionários
                result = [dict(zip(columns, row)) for row in result.fetchall()]
                return result
            except Exception as exception:
                db.session.rollback()
                raise exception
