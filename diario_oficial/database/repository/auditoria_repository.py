from datetime import date

from sqlalchemy import text

from diario_oficial.auditoria import Ato, Edicao, Publicacao

from ..configs.connection import DBConnectionHandler


class AuditoriaRepository:
    """Consultas e gravação do resultado da auditoria da separação em atos."""

    def update_auditoria(self, resultados: dict[int, bool]) -> None:
        """Grava publicacao.auditoria de uma só vez: ou todas as publicações, ou nenhuma.

        Args:
            resultados (dict[int, bool]): id da publicação e resultado da auditoria
        """
        if not resultados:
            return
        with DBConnectionHandler() as db:
            try:
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
