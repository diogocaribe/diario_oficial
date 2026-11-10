from datetime import date

from sqlalchemy import text

from diario_oficial.auditoria import (
    Ato,
    Edicao,
    Publicacao,
    RelatorioDia,
    linhas_de_log,
)

from ..configs.connection import DBConnectionHandler
from .log_erro_repository import INSERIR_LOG_ERRO


class AuditoriaRepository:
    """Consultas e gravação do resultado da auditoria da separação em atos."""

    def salvar_relatorio(self, relatorio: RelatorioDia) -> None:
        """Grava publicacao.auditoria e os achados no log, na mesma transação.

        Cada lado é testado à parte: uma edição sem publicações ainda pode ter achado.

        Args:
            relatorio (RelatorioDia): resultado da auditoria de uma edição
        """
        resultados = relatorio.resultado_publicacoes
        linhas = linhas_de_log(relatorio)
        if not resultados and not linhas:
            return
        with DBConnectionHandler() as db:
            try:
                if resultados:
                    db.session.execute(
                        text(
                            'UPDATE processing.publicacao SET auditoria = :auditoria '
                            'WHERE id = :id'
                        ),
                        [
                            {'id': id_publicacao, 'auditoria': resultado}
                            for id_publicacao, resultado in resultados.items()
                        ],
                    )
                if linhas:
                    db.session.execute(INSERIR_LOG_ERRO, linhas)
                db.session.commit()
            except Exception as exception:
                db.session.rollback()
                raise exception

    def get_publicacoes_reprovadas(self):
        """Publicações com texto e auditoria reprovada, de todas as datas."""
        with DBConnectionHandler() as db:
            return db.session.execute(
                text("""
                    SELECT p.id, p.doe_bruto_id, p.link, p.conteudo_link, d.dt_edicao
                    FROM processing.publicacao p
                    JOIN processing.doe_bruto d ON d.id = p.doe_bruto_id
                    WHERE p.auditoria IS FALSE
                      AND COALESCE(p.conteudo_link, '') <> ''
                    ORDER BY d.dt_edicao, p.id
                """)
            ).all()

    def voltar_para_separacao(self, ids_publicacao: list[int]) -> None:
        """Apaga os atos das publicações e as devolve à fila de separação.

        O UPDATE cobre a publicação sem atos, na qual o trigger de processing.ato não
        dispara.

        Args:
            ids_publicacao (list[int]): ids das publicações a reprocessar
        """
        parametros = {'ids': ids_publicacao}
        with DBConnectionHandler() as db:
            try:
                db.session.execute(
                    text('DELETE FROM processing.ato WHERE publicacao_id = ANY(:ids)'),
                    parametros,
                )
                db.session.execute(
                    text(
                        'UPDATE processing.publicacao SET processada_para_ato = NULL '
                        'WHERE id = ANY(:ids)'
                    ),
                    parametros,
                )
                db.session.commit()
            except Exception as exception:
                db.session.rollback()
                raise exception

    def get_edicao(self, data: date) -> Edicao | None:
        """Edição da data com suas publicações e atos, ou None se não foi coletada."""
        with DBConnectionHandler() as db:
            linha_edicao = db.session.execute(
                text("""
                    SELECT id, dt_edicao, existe, doe_bruto_para_publicacao
                    FROM processing.doe_bruto
                    WHERE dt_edicao = :data
                """),
                {'data': data},
            ).first()
            if linha_edicao is None:
                return None
            filtro = {'doe_bruto_id': linha_edicao.id}
            linhas_publicacao = db.session.execute(
                text("""
                    SELECT id, nome_ato, link, conteudo_link, processada_para_ato
                    FROM processing.publicacao
                    WHERE doe_bruto_id = :doe_bruto_id
                    ORDER BY id
                """),
                filtro,
            ).all()
            linhas_ato = db.session.execute(
                text("""
                    SELECT a.id, a.publicacao_id, a.conteudo_ato
                    FROM processing.ato a
                    JOIN processing.publicacao p ON p.id = a.publicacao_id
                    WHERE p.doe_bruto_id = :doe_bruto_id
                    ORDER BY a.id
                """),
                filtro,
            ).all()

        edicao = Edicao(
            linha_edicao.dt_edicao,
            linha_edicao.existe,
            linha_edicao.doe_bruto_para_publicacao,
            id=linha_edicao.id,
        )
        publicacoes = {}
        for linha in linhas_publicacao:
            publicacao = Publicacao(
                linha.id,
                linha.nome_ato,
                linha.conteudo_link,
                linha.processada_para_ato,
                link=linha.link,
            )
            publicacoes[linha.id] = publicacao
            edicao.publicacoes.append(publicacao)
        for linha in linhas_ato:
            publicacoes[linha.publicacao_id].atos.append(
                Ato(linha.id, linha.conteudo_ato)
            )
        return edicao
