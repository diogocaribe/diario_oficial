from datetime import date

from sqlalchemy import text

from diario_oficial.tipo_ato import TipoAto

from ..configs.connection import DBConnectionHandler


class TipoAtoRepository:
    """Consultas e gravação dos tipos de ato encontrados em cada ato."""

    def get_catalogo(self) -> list[TipoAto]:
        """Todos os tipos de dominio.tipo_ato."""
        with DBConnectionHandler() as db:
            linhas = db.session.execute(
                text('SELECT id, nome, sigla FROM dominio.tipo_ato ORDER BY id')
            ).all()
        return [TipoAto(*linha) for linha in linhas]

    def get_atos_pendentes(self, data: date | None = None):
        """Atos de publicações aprovadas na auditoria, ainda sem tipo gravado.

        Ato em que nenhum tipo foi encontrado volta a ser analisado na execução seguinte,
        o que permite aproveitar nomes novos incluídos no domínio.

        Args:
            data (date, optional): restringe à edição dessa data. Padrão é todas as datas.
        """
        with DBConnectionHandler() as db:
            return db.session.execute(
                text("""
                    SELECT a.id, a.conteudo_ato
                    FROM processing.ato a
                    JOIN processing.publicacao p ON p.id = a.publicacao_id
                    JOIN processing.doe_bruto d ON d.id = p.doe_bruto_id
                    WHERE p.auditoria IS TRUE
                      AND (CAST(:data AS date) IS NULL
                           OR d.dt_edicao = CAST(:data AS date))
                      AND NOT EXISTS (
                          SELECT 1 FROM processing.ato_tipo_ato ata
                          WHERE ata.ato_id = a.id
                      )
                    ORDER BY a.id
                """),
                {'data': data},
            ).all()

    def salvar(self, linhas: list[dict]) -> None:
        """Grava os pares ato/tipo, ignorando os que já existem.

        Args:
            linhas (list[dict]): dicts com as chaves ato_id e tipo_ato_id
        """
        if not linhas:
            return
        with DBConnectionHandler() as db:
            try:
                db.session.execute(
                    text("""
                        INSERT INTO processing.ato_tipo_ato (ato_id, tipo_ato_id)
                        VALUES (:ato_id, :tipo_ato_id)
                        ON CONFLICT DO NOTHING
                    """),
                    linhas,
                )
                db.session.commit()
            except Exception as exception:
                db.session.rollback()
                raise exception
