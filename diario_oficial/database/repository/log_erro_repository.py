from sqlalchemy import text

from ..configs.connection import DBConnectionHandler

# Espera as chaves: etapa, tipo, descricao, trecho, doe_bruto_id, publicacao_id, ato_id
# Só insere ocorrência ainda não registrada: publicações pendentes e novas auditorias
# encontram os mesmos erros a cada execução. ato_id fica fora da comparação porque muda
# quando a publicação é reprocessada.
INSERIR_LOG_ERRO = text("""
    INSERT INTO processing.log_erro
        (etapa, tipo, descricao, trecho, doe_bruto_id, publicacao_id, ato_id)
    SELECT novo.*
    FROM (
        SELECT
            CAST(:etapa AS varchar) AS etapa,
            CAST(:tipo AS varchar) AS tipo,
            CAST(:descricao AS text) AS descricao,
            CAST(:trecho AS text) AS trecho,
            CAST(:doe_bruto_id AS integer) AS doe_bruto_id,
            CAST(:publicacao_id AS integer) AS publicacao_id,
            CAST(:ato_id AS integer) AS ato_id
    ) AS novo
    WHERE NOT EXISTS (
        SELECT 1
        FROM processing.log_erro AS atual
        WHERE atual.etapa = novo.etapa
          AND atual.tipo = novo.tipo
          AND atual.descricao = novo.descricao
          AND atual.doe_bruto_id = novo.doe_bruto_id
          AND atual.publicacao_id IS NOT DISTINCT FROM novo.publicacao_id
          AND atual.trecho IS NOT DISTINCT FROM novo.trecho
    )
""")


class LogErroRepository:
    """Gravação do histórico de erros em processing.log_erro."""

    def registrar(self, linhas: list[dict]) -> None:
        """Insere de uma só vez as linhas de log ainda não registradas.

        Args:
            linhas (list[dict]): valores de cada linha, com as chaves de INSERIR_LOG_ERRO
        """
        if not linhas:
            return
        with DBConnectionHandler() as db:
            try:
                db.session.execute(INSERIR_LOG_ERRO, linhas)
                db.session.commit()
            except Exception as exception:
                db.session.rollback()
                raise exception
